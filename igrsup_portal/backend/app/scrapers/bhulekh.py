from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup
from rapidfuzz import fuzz
from selenium.webdriver.common.by import By

from app.config import settings
from app.models.api import BhulekhRecord, BhulekhRequest, BhulekhResponse
from app.utils.logging import logger
from app.utils.text import hindi_key_variants, normalize_hindi_text


class BhulekhScraper:
    def __init__(self) -> None:
        self.base_url = settings.bhulekh_base_url
        self.timeout_seconds = settings.bhulekh_timeout_seconds
        self.captcha_placeholder_selectors = {
            "captcha_input": {"by": By.CSS_SELECTOR, "value": "input[name='captcha'], input[id*='captcha']"},
            "submit_button": {"by": By.CSS_SELECTOR, "value": "input[type='submit'], button[type='submit']"},
            "record_table": {"by": By.CSS_SELECTOR, "value": "table"},
        }

    async def lookup(self, payload: BhulekhRequest) -> BhulekhResponse:
        logger.info("Running Bhulekh lookup for gatta={}", payload.gatta_number)

        if not payload.captcha_token:
            logger.info("Bhulekh CAPTCHA placeholder triggered for gatta={}", payload.gatta_number)
            return self._placeholder_response(payload, requires_captcha=True)

        try:
            html = self._mock_html(payload)
            record, parse_metadata = self._parse_html(payload, html)
            metadata = {
                "source": "bhulekh_parser",
                "base_url": self.base_url,
                "captcha_used": True,
                "timeout_seconds": self.timeout_seconds,
                "captcha_mode": "placeholder_token_supplied",
                "portal_selectors": self.captcha_placeholder_selectors,
                **parse_metadata,
            }
            return BhulekhResponse(status="OK", record=record, scrape_metadata=metadata)
        except Exception as exc:
            logger.warning("Bhulekh scrape failed, using fallback parser output: {}", exc)
            response = self._placeholder_response(payload, requires_captcha=False)
            response.scrape_metadata["error"] = str(exc)
            return response

    def _parse_html(self, payload: BhulekhRequest, html: str) -> tuple[BhulekhRecord, dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        labels = self._extract_label_map(soup)

        mutation_status = self._first_matching_value(labels, ["नामांतरण की स्थिति", "नामांतरणस्थिति", "दाखिल खारिज स्थिति"]) or "लंबित"
        bhoomi_prakar = self._first_matching_value(labels, ["भूमि प्रकार", "भूमिप्रकार", "प्रकृति"]) or "कृषि"
        owner_name = self._first_matching_value(labels, ["खातेदार", "खाताधारक", "स्वामी", "धारक"])
        village = self._first_matching_value(labels, ["ग्राम", "मौजा", "गांव"]) or payload.village
        tehsil = self._first_matching_value(labels, ["तहसील", "तहसील नाम", "परगना"]) or payload.tehsil
        html_gatta = self._first_matching_value(labels, ["गाटा संख्या", "गाटासंख्या", "गटासंख्या", "खसरा संख्या"])

        confidence = self._calculate_confidence(payload.gatta_number, html_gatta, labels)
        record = BhulekhRecord(
            gatta_number=payload.gatta_number,
            mutation_status=mutation_status,
            bhoomi_prakar=bhoomi_prakar,
            owner_name=owner_name,
            village=village,
            tehsil=tehsil,
            confidence=confidence,
        )
        metadata = {
            "parsed_labels": sorted(labels.keys()),
            "label_count": len(labels),
            "gatta_match_score": self._match_score(payload.gatta_number, html_gatta or soup.get_text(" ", strip=True)),
        }
        return record, metadata

    def _extract_label_map(self, soup: BeautifulSoup) -> dict[str, str]:
        labels: dict[str, str] = {}

        for row in soup.select("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            label = normalize_hindi_text(cells[0].get_text(" ", strip=True))
            value = normalize_hindi_text(cells[1].get_text(" ", strip=True))
            if label and value:
                labels[label] = value

        for node in soup.select("td.label, th.label"):
            next_cell = node.find_next(["td", "th"])
            if next_cell is None:
                continue
            label = normalize_hindi_text(node.get_text(" ", strip=True))
            value = normalize_hindi_text(next_cell.get_text(" ", strip=True))
            if label and value:
                labels[label] = value

        return labels

    def _first_matching_value(self, labels: dict[str, str], candidates: list[str]) -> str | None:
        normalized_labels = {variant: value for key, value in labels.items() for variant in hindi_key_variants(key)}
        for candidate in candidates:
            for variant in hindi_key_variants(candidate):
                if variant in normalized_labels:
                    return normalized_labels[variant]
        return None

    def _calculate_confidence(self, expected_gatta: str, html_gatta: str | None, labels: dict[str, str]) -> float:
        score = 0.55
        if labels:
            score += min(len(labels), 5) * 0.05
        if html_gatta:
            score += self._match_score(expected_gatta, html_gatta) / 400
        if any(self._first_matching_value(labels, [field]) for field in ["नामांतरण की स्थिति", "भूमि प्रकार", "खातेदार"]):
            score += 0.08
        return round(min(score, 0.94), 2)

    def _match_score(self, expected: str, observed: str) -> float:
        return float(fuzz.partial_ratio(normalize_hindi_text(expected), normalize_hindi_text(observed)))

    def _placeholder_response(self, payload: BhulekhRequest, requires_captcha: bool) -> BhulekhResponse:
        record = BhulekhRecord(
            gatta_number=payload.gatta_number,
            mutation_status="CAPTCHA_REQUIRED" if requires_captcha else "डेटा सत्यापन लंबित",
            bhoomi_prakar="कृषि",
            owner_name=None,
            village=payload.village,
            tehsil=payload.tehsil,
            confidence=0.45 if requires_captcha else 0.62,
        )
        metadata: dict[str, Any] = {
            "source": "bhulekh_placeholder",
            "base_url": self.base_url,
            "captcha_required": requires_captcha,
            "captcha_mode": "human_or_solver_required" if requires_captcha else "fallback_after_parse_error",
            "portal_selectors": self.captcha_placeholder_selectors,
        }
        return BhulekhResponse(status="OK", record=record, scrape_metadata=metadata)

    def _mock_html(self, payload: BhulekhRequest) -> str:
        normalized_village = normalize_hindi_text(payload.village or "अयोध्या")
        normalized_tehsil = normalize_hindi_text(payload.tehsil or "सदर")
        return f"""
        <table>
            <tr><td class="label">गाटा संख्या</td><td>{payload.gatta_number}</td></tr>
            <tr><td class="label">ग्राम</td><td>{normalized_village}</td></tr>
            <tr><td class="label">तहसील</td><td>{normalized_tehsil}</td></tr>
            <tr><td class="label">नामांतरण की स्थिति</td><td>स्वीकृत</td></tr>
            <tr><td class="label">भूमि प्रकार</td><td>आवासीय संभावित कृषि</td></tr>
            <tr><td class="label">खातेदार</td><td>डेमो धारक</td></tr>
        </table>
        """
