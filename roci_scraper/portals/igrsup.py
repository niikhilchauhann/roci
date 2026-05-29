from __future__ import annotations

import json
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from .base import PortalAdapter, PortalResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IGRSUP_BASE = "https://igrsup.gov.in"
_SEARCH_URL  = f"{_IGRSUP_BASE}/igrsup/us_newPropertySearchAction"
_DETAIL_URL  = f"{_IGRSUP_BASE}/igrsup/propertySearchViewDetail"

_SESSION_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "igrsup_portal" / "backend"
    / "data" / "sessions" / "igrsup-session.json"
)
_VILLAGES_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "igrsup_portal" / "backend"
    / "data" / "input" / "villages.json"
)
_CIRCLE_RATES_FILE = (
    Path(__file__).resolve().parent.parent / "ref_data" / "circle_rates.json"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Origin":          _IGRSUP_BASE,
    "Referer":         _SEARCH_URL,
    "Content-Type":    "application/x-www-form-urlencoded",
}

# Tehsil name → IGRSUP SRO code (mirrors bhunaksha._TEHSILS mapping)
_TEHSIL_TO_SRO: Dict[str, str] = {
    "sadar":    "120",
    "ayodhya":  "120",  # historic / alternate name for Sadar
    "faizabad": "120",  # historic name
    "bikapur":  "121",
    "milkipur": "122",
    "rudauli":  "074",
    "sohaval":  "123",
    "sohawal":  "123",
}

_DISTRICT_CODE = "177"  # Ayodhya


# ---------------------------------------------------------------------------
# Session loader  (Playwright storageState format)
# ---------------------------------------------------------------------------

def _load_cookies() -> Dict[str, str]:
    if not _SESSION_FILE.exists():
        raise FileNotFoundError(
            f"IGRSUP session not found: {_SESSION_FILE}. "
            "Run: cd 'igrsup_portal/backend' && node scripts/login-and-save-session.js"
        )
    raw = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
    cookies_list = raw.get("cookies", raw) if isinstance(raw, dict) else raw
    return {c["name"]: c["value"] for c in cookies_list}


# ---------------------------------------------------------------------------
# Reverse geocode → tehsil (reuses same Nominatim call as bhunaksha)
# ---------------------------------------------------------------------------

_NOMINATIM_LAST = 0.0


def _reverse_geocode(lat: float, lng: float) -> Dict[str, str]:
    global _NOMINATIM_LAST
    gap = time.monotonic() - _NOMINATIM_LAST
    if gap < 1.0:
        time.sleep(1.0 - gap)
    _NOMINATIM_LAST = time.monotonic()
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "zoom": 16, "addressdetails": 1},
            headers={"User-Agent": "roci-engine/0.1"},
            timeout=10,
        )
        if r.ok:
            return r.json().get("address", {})
    except Exception as exc:
        logger.warning("[igrsup] Nominatim error: {}", exc)
    return {}


def _pick_sro_code(address: Dict[str, str]) -> str:
    """Map Nominatim address to an IGRSUP SRO code using the same tehsil names as bhunaksha."""
    candidates = [
        address.get("county", ""),
        address.get("state_district", ""),
        address.get("suburb", ""),
        address.get("city_district", ""),
    ]
    for cand in candidates:
        key = cand.lower().strip()
        if key in _TEHSIL_TO_SRO:
            return _TEHSIL_TO_SRO[key]
        for name, code in _TEHSIL_TO_SRO.items():
            if name in key or key in name:
                return code
    logger.info("[igrsup] Could not determine SRO from geocode — defaulting to Sadar (120)")
    return "120"


# ---------------------------------------------------------------------------
# Villages.json lookup — get a valid gaonCode for the given SRO
# ---------------------------------------------------------------------------

def _load_villages() -> List[Dict]:
    if not _VILLAGES_FILE.exists():
        return []
    return json.loads(_VILLAGES_FILE.read_text(encoding="utf-8"))


def _get_gaon_code(villages: List[Dict], district_code: str, sro_code: str) -> str:
    """Return the first gaonCode in villages.json for the given district+SRO.
    The form requires a village code to trigger the search, but IGRSUP returns
    SRO-wide deed data regardless of which village is passed."""
    for v in villages:
        if v.get("districtCode") == district_code and v.get("sroCode") == sro_code:
            return v["gaonCode"]
    return ""


# ---------------------------------------------------------------------------
# Circle rate lookup
# ---------------------------------------------------------------------------

def _lookup_circle_rate(district: str, tehsil: str | None) -> Optional[float]:
    """Return verified circle rate in crore/acre, or None if not yet available."""
    if not _CIRCLE_RATES_FILE.exists():
        return None
    data = json.loads(_CIRCLE_RATES_FILE.read_text(encoding="utf-8"))
    district_data = data.get(district)
    if not district_data:
        return None
    if tehsil:
        entry = district_data.get(tehsil)
        if entry:
            val = entry.get("circle_rate_crore_per_acre")
            return float(val) if val is not None else None
    val = district_data.get("__tehsil_default", {}).get("circle_rate_crore_per_acre")
    return float(val) if val is not None else None


# ---------------------------------------------------------------------------
# Date parsing  — "15 FEB 2025" → datetime
# ---------------------------------------------------------------------------

_MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
    "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _parse_reg_date(date_str: str) -> Optional[datetime]:
    parts = date_str.strip().upper().split()
    if len(parts) == 3:
        try:
            day   = int(parts[0])
            month = _MONTH_MAP.get(parts[1][:3])
            year  = int(parts[2])
            if month:
                return datetime(year, month, day, tzinfo=timezone.utc)
        except (ValueError, KeyError):
            pass
    return None


# ---------------------------------------------------------------------------
# Deed search — parse one village's tablepaging HTML into row dicts
# ---------------------------------------------------------------------------

def _parse_deed_html(html: str) -> List[Dict[str, Any]]:
    soup  = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tablepaging")
    if not table:
        return []

    rows: List[Dict[str, Any]] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 10:
            continue
        cols = [td.get_text(separator=" ", strip=True) for td in tds]
        if "पंजी. वर्ष" in cols[1] or cols[0] in ("क्र.सं.", "क्र.सं"):
            continue   # header row

        row: Dict[str, Any] = {
            "registration_year": cols[1],
            "registration_no":   cols[2],
            "party_name":        cols[3],
            "address":           cols[4],
            "property_details":  cols[5],
            "khasra":            cols[6],
            "registration_date": cols[7],
            "deed_type":         cols[8],
            "_reg_date":         _parse_reg_date(cols[7]),
        }
        form_tag = tds[9].find("form")
        if form_tag:
            row["_detail"] = {
                inp.get("name"): inp.get("value", "")
                for inp in form_tag.find_all("input")
                if inp.get("name")
            }
        rows.append(row)

    return rows


def _fetch_one_village(
    cookies: Dict[str, str],
    sro_code: str,
    gaon_code: str,
) -> List[Dict[str, Any]]:
    form = {
        "districtCode":                       _DISTRICT_CODE,
        "sroCode":                            sro_code,
        "propertyId":                         "",
        "propNEWAddress":                     "",
        "gaonCode1":                          gaon_code,
        "action:getPropertyDeedSearchDetail": "सम्पत्ति विलेख विवरण(Property Deed)",
    }
    try:
        resp = requests.post(
            _SEARCH_URL, data=form, cookies=cookies,
            headers=_HEADERS, timeout=20,
        )
        resp.raise_for_status()
        return _parse_deed_html(resp.text)
    except Exception as exc:
        logger.debug("[igrsup] village {} fetch error: {}", gaon_code, exc)
        return []


def _fetch_all_villages(
    cookies: Dict[str, str],
    villages: List[Dict],
    sro_code: str,
    max_workers: int = 10,
) -> List[Dict[str, Any]]:
    """
    Fetch deed rows for every village in the given SRO concurrently.
    Deduplicates on (registration_year, registration_no) — the unique deed key within an SRO.
    """
    gaon_codes = [
        v["gaonCode"] for v in villages
        if v.get("sroCode") == sro_code and v.get("districtCode") == _DISTRICT_CODE
    ]

    seen: set[tuple] = set()
    all_rows: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_one_village, cookies, sro_code, gc): gc
            for gc in gaon_codes
        }
        for fut in as_completed(futures):
            for row in fut.result():
                key = (row["registration_year"], row["registration_no"])
                if key not in seen:
                    seen.add(key)
                    all_rows.append(row)

    return all_rows


# ---------------------------------------------------------------------------
# Deed detail — fetch consideration (प्रतिफल) and plot area
# ---------------------------------------------------------------------------

_RE_AMOUNT = re.compile(r"\d[\d,]+")
# Matches area values like "1200 sqft", "120.5 वर्ग मीटर", "0.5 बीघा"
_RE_SQM   = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:sqm|sq\.?\s*m|वर्ग\s*मीटर|square\s*met)", re.I)
_RE_SQFT  = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:sqft|sq\.?\s*ft|वर्ग\s*फीट|square\s*feet?)", re.I)
_RE_BISWA = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:biswa|बिस्वा)", re.I)

_SQM_PER_BISWA = 125.418  # 1 biswa (UP) ≈ 125.4 sqm


def _area_to_sqft(text: str) -> Optional[float]:
    """Extract plot area from a text snippet and return it in sqft."""
    m = _RE_SQFT.search(text)
    if m:
        return float(m.group(1).replace(",", ""))
    m = _RE_SQM.search(text)
    if m:
        return float(m.group(1).replace(",", "")) * 10.7639
    m = _RE_BISWA.search(text)
    if m:
        return float(m.group(1).replace(",", "")) * _SQM_PER_BISWA * 10.7639
    return None


def _fetch_deed_detail(
    cookies: Dict[str, str], detail_fields: Dict
) -> tuple[Optional[int], Optional[float]]:
    """Return (consideration_inr, area_sqft) from a deed detail page, or (None, None)."""
    try:
        resp = requests.post(
            _DETAIL_URL, data=detail_fields,
            cookies=cookies, headers=_HEADERS, timeout=20,
        )
        resp.raise_for_status()
        soup  = BeautifulSoup(resp.text, "html.parser")
        lines = [l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip()]

        consideration: Optional[int] = None
        area_sqft: Optional[float]   = None

        for i, line in enumerate(lines):
            # Consideration amount
            if consideration is None and "प्रतिफल" in line:
                for candidate in lines[i + 1: i + 4]:
                    m = _RE_AMOUNT.search(candidate.replace(",", ""))
                    if m:
                        consideration = int(m.group().replace(",", ""))
                        break
            # Plot area — look for area keywords
            if area_sqft is None and any(
                kw in line for kw in ("क्षेत्रफल", "area", "Area", "sqft", "sqm", "बिस्वा")
            ):
                for candidate in lines[i: i + 3]:
                    a = _area_to_sqft(candidate)
                    if a and a > 1:
                        area_sqft = a
                        break

        return consideration, area_sqft
    except Exception:
        return None, None


def _median_price_per_sqft(
    cookies: Dict[str, str], rows: List[Dict], max_fetch: int
) -> Optional[float]:
    """
    Fetch deed detail pages (up to max_fetch), compute ₹/sqft for each,
    and return the median. Returns None if no valid data points.
    """
    prices: List[float] = []
    for row in rows[:max_fetch]:
        detail = row.get("_detail")
        if not detail:
            continue
        consideration, area_sqft = _fetch_deed_detail(cookies, detail)
        if consideration and area_sqft and consideration > 0 and area_sqft > 0:
            prices.append(consideration / area_sqft)
    return round(statistics.median(prices), 2) if prices else None


# ---------------------------------------------------------------------------
# 90-day window filter
# ---------------------------------------------------------------------------

def _filter_90_days(rows: List[Dict], cutoff: datetime, end: datetime) -> List[Dict]:
    """Keep rows whose registration_date falls within [cutoff, end)."""
    return [
        r for r in rows
        if r.get("_reg_date") and cutoff <= r["_reg_date"] < end
    ]


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class IgrsupAdapter(PortalAdapter):
    portal_name = "igrsup"
    url         = _IGRSUP_BASE

    _MAX_DETAIL_FETCHES = 5  # detail pages fetched per window for price averaging

    def scrape(
        self,
        *,
        lat: float,
        lng: float,
        district: str,
        gatta_number: str | None = None,
        output_dir: Path | None = None,
        headless: bool = True,
    ) -> PortalResult:
        query: Dict[str, Any] = {
            "lat": lat, "lng": lng,
            "district": district, "gatta_number": gatta_number,
        }

        try:
            cookies  = _load_cookies()
            villages = _load_villages()
            if not villages:
                raise RuntimeError(f"No villages data at {_VILLAGES_FILE}")

            # 1. Reverse geocode → tehsil → SRO code (same logic as bhunaksha)
            address  = _reverse_geocode(lat, lng)
            sro_code = _pick_sro_code(address)
            sro_name = next(
                (v["sro"] for v in villages if v.get("sroCode") == sro_code), sro_code
            )

            # 2. 90-day windows
            now           = datetime.now(timezone.utc)
            current_start = now - timedelta(days=90)
            current_end   = now
            prev_start    = now - timedelta(days=180)
            prev_end      = current_start

            logger.info(
                "[igrsup] deed search: district={} sro={} ({}) | "
                "current={} — {} | previous={} — {}",
                _DISTRICT_CODE, sro_code, sro_name,
                current_start.strftime("%Y-%m-%d"), current_end.strftime("%Y-%m-%d"),
                prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d"),
            )

            # 3. Fetch deed rows for every village in the tehsil concurrently
            logger.info("[igrsup] fetching all villages for SRO {} ({})", sro_code, sro_name)
            all_rows = _fetch_all_villages(cookies, villages, sro_code)
            logger.info("[igrsup] fetched {} unique deed rows across all villages in SRO {}", len(all_rows), sro_name)

            # 4. Filter to 90-day windows
            current_rows = _filter_90_days(all_rows, current_start, current_end)
            previous_rows = _filter_90_days(all_rows, prev_start, prev_end)

            n_current  = len(current_rows)
            n_previous = len(previous_rows)

            # 5. Fetch deed details — median ₹/sqft per window (up to 5 deeds each)
            logger.info("[igrsup] fetching deed details for price/sqft calculation")
            p_current_median  = _median_price_per_sqft(cookies, current_rows,  self._MAX_DETAIL_FETCHES)
            p_previous_median = _median_price_per_sqft(cookies, previous_rows, self._MAX_DETAIL_FETCHES)

            # deed_ref: registration number of the most recent deed in current window
            deed_ref: Optional[str] = None
            if current_rows:
                sorted_rows = sorted(
                    (r for r in current_rows if r.get("_reg_date")),
                    key=lambda r: r["_reg_date"],
                    reverse=True,
                )
                if sorted_rows:
                    deed_ref = sorted_rows[0].get("registration_no")

            # 6. Circle rate from static reference table
            circle_rate = _lookup_circle_rate(district, tehsil=sro_name or None)

            data: Dict[str, Any] = {
                # Scorer inputs (spec field names)
                "n_current":          n_current,
                "n_previous":         n_previous,
                "p_current_median":   p_current_median,
                "p_previous_median":  p_previous_median,
                "deed_ref":           deed_ref,
                # Provenance
                "circle_rate_crore_per_acre": circle_rate,
                "current_window_start":       current_start.strftime("%Y-%m-%d"),
                "current_window_end":         current_end.strftime("%Y-%m-%d"),
                "previous_window_start":      prev_start.strftime("%Y-%m-%d"),
                "previous_window_end":        prev_end.strftime("%Y-%m-%d"),
                "total_records_in_response":  len(all_rows),
                "sro_code": sro_code,
                "sro_name": sro_name,
            }

            status = "OK" if len(all_rows) > 0 else "EMPTY_PAGE"
            note = (
                f"n_current={n_current} (90d), n_previous={n_previous} (prior 90d), "
                f"p_current_median=₹{p_current_median:,.0f}/sqft" if p_current_median else
                f"n_current={n_current} (90d), n_previous={n_previous} (prior 90d), p_current_median=N/A"
            )
            result = PortalResult(
                self.portal_name, status, self.url, query, data, note=note,
            )

        except FileNotFoundError as exc:
            logger.warning("[igrsup] session missing: {}", exc)
            result = PortalResult(
                self.portal_name, "SESSION_MISSING", self.url, query, {}, note=str(exc),
            )
        except Exception as exc:
            logger.warning("[igrsup] scrape failed: {}", exc)
            result = PortalResult(
                self.portal_name, "ERROR", self.url, query, {}, note=str(exc),
            )

        self._save(output_dir, result)
        return result


# ---------------------------------------------------------------------------
# Cached adapter — reads from out/igrsup_sro_cache.json, no network calls
# ---------------------------------------------------------------------------

_CACHE_FILE = (
    Path(__file__).resolve().parent.parent.parent / "out" / "igrsup_sro_cache.json"
)

_SRO_CODE_TO_NAME = {v: k for k, v in _TEHSIL_TO_SRO.items()}


class CachedIgrsupAdapter(PortalAdapter):
    """Serves IGRSUP data from the pre-built SRO cache instead of live scraping."""

    portal_name = "igrsup"
    url         = _IGRSUP_BASE

    def scrape(
        self,
        *,
        lat: float,
        lng: float,
        district: str,
        gatta_number: str | None = None,
        output_dir: Path | None = None,
        headless: bool = True,
    ) -> PortalResult:
        query: Dict[str, Any] = {
            "lat": lat, "lng": lng,
            "district": district, "gatta_number": gatta_number,
        }

        try:
            if not _CACHE_FILE.exists():
                raise FileNotFoundError(
                    f"IGRSUP cache not found: {_CACHE_FILE}. "
                    "Run: python scripts/cache_igrsup_sros.py"
                )

            cache = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            meta  = cache.get("__meta", {})
            sros  = cache.get("sros", {})

            # Reverse geocode → SRO code (same as live adapter)
            address  = _reverse_geocode(lat, lng)
            sro_code = _pick_sro_code(address)
            entry    = sros.get(sro_code)

            if not entry:
                raise KeyError(f"SRO {sro_code} not found in cache — run cache script first")

            data: Dict[str, Any] = {
                "n_current":          entry.get("n_current"),
                "n_previous":         entry.get("n_previous"),
                "p_current":          entry.get("p_current_median"),
                "p_previous":         entry.get("p_previous_median"),
                "deed_ref":           entry.get("deed_ref"),
                "mu_district":        meta.get("mu_district"),
                "sigma_district":     meta.get("sigma_district"),
                "circle_rate_crore_per_acre": entry.get("circle_rate_crore_per_acre"),
                "current_window_start":  entry.get("current_window_start"),
                "current_window_end":    entry.get("current_window_end"),
                "previous_window_start": entry.get("previous_window_start"),
                "previous_window_end":   entry.get("previous_window_end"),
                "sro_code": sro_code,
                "sro_name": entry.get("sro_name"),
                "cache_fetched_at": entry.get("fetched_at"),
            }

            n_current = entry.get("n_current", 0)
            note = (
                f"[CACHE] n_current={n_current}, n_previous={entry.get('n_previous')}, "
                f"p_current_median={entry.get('p_current_median')}, "
                f"fetched_at={entry.get('fetched_at')}"
            )
            status = "OK" if n_current > 0 else "EMPTY_PAGE"
            result = PortalResult(self.portal_name, status, self.url, query, data, note=note)

        except FileNotFoundError as exc:
            logger.warning("[igrsup_cache] cache missing: {}", exc)
            result = PortalResult(self.portal_name, "CACHE_MISSING", self.url, query, {}, note=str(exc))
        except Exception as exc:
            logger.warning("[igrsup_cache] failed: {}", exc)
            result = PortalResult(self.portal_name, "ERROR", self.url, query, {}, note=str(exc))

        self._save(output_dir, result)
        return result
