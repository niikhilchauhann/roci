from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from .base import PortalAdapter, PortalResult
from ..geo import classify_tender_type, parse_stage, infer_project_distance

_PORTAL = 'https://eprocure.gov.in/eprocure/app'
_LOCATION_PAGE = f'{_PORTAL}?component=$RandomId&page=FrontEndTendersByLocation&service=page'
_MAX_CAPTCHA_RETRIES = 10

_GEM_SEARCH_URL = 'https://mkp.gem.gov.in/api/public/getSearchBidList'
_GEM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json',
    'Referer': 'https://gem.gov.in/',
}

_easyocr_reader = None
_dddd_ocr = None

_OCR_ALLOWLIST = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'


def _get_easyocr():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _easyocr_reader


def _get_dddd_ocr():
    global _dddd_ocr
    if _dddd_ocr is None:
        import ddddocr
        _dddd_ocr = ddddocr.DdddOcr(show_ad=False)
    return _dddd_ocr


def _preprocess_captcha(img_bytes: bytes) -> list:
    """Return multiple preprocessed variants of the CAPTCHA image for OCR."""
    try:
        from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageFile
        import io
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        img = Image.open(io.BytesIO(img_bytes)).convert('L')

        variants = []

        # 1. Median filter (suppress dot noise)
        v1 = img.filter(ImageFilter.MedianFilter(size=3))
        buf = io.BytesIO(); v1.save(buf, format='PNG'); variants.append(buf.getvalue())

        # 2. Threshold (binarise) — removes background noise
        v2 = img.point(lambda x: 0 if x < 140 else 255)
        buf = io.BytesIO(); v2.save(buf, format='PNG'); variants.append(buf.getvalue())

        # 3. Inverted + threshold — works when text is light on dark background
        v3 = ImageOps.invert(img).point(lambda x: 0 if x < 140 else 255)
        buf = io.BytesIO(); v3.save(buf, format='PNG'); variants.append(buf.getvalue())

        # 4. Contrast boost + median
        v4 = ImageEnhance.Contrast(img).enhance(3.0).filter(ImageFilter.MedianFilter(size=3))
        buf = io.BytesIO(); v4.save(buf, format='PNG'); variants.append(buf.getvalue())

        return variants
    except Exception:
        return [img_bytes]


def _solve_captcha(img_bytes: bytes) -> str:
    """
    Solve CPPP CAPTCHA. Tries multiple image preprocessing variants with
    EasyOCR (primary) and ddddocr (fallback) for each variant.
    Returns alphanumeric string, empty string on complete failure.
    """
    variants = _preprocess_captcha(img_bytes)

    for filtered in variants:
        # Primary: EasyOCR (handles case correctly)
        try:
            reader = _get_easyocr()
            parts = reader.readtext(filtered, detail=0, allowlist=_OCR_ALLOWLIST)
            text = ''.join(parts).strip().replace(' ', '')
            if 4 <= len(text) <= 8 and text.isalnum():
                return text
        except Exception:
            pass

        # Fallback: ddddocr
        try:
            ocr = _get_dddd_ocr()
            text = ocr.classification(filtered).strip().replace(' ', '')
            if 4 <= len(text) <= 8 and text.isalnum():
                return text.upper()
        except Exception:
            pass

    # Last resort: EasyOCR on original
    try:
        reader = _get_easyocr()
        parts = reader.readtext(img_bytes, detail=0, allowlist=_OCR_ALLOWLIST)
        text = ''.join(parts).strip().replace(' ', '')
        if 4 <= len(text) <= 8 and text.isalnum():
            return text
    except Exception:
        pass

    return ''


def _captcha_bytes(page) -> bytes:
    """Return PNG bytes of the CPPP CAPTCHA via element screenshot."""
    # Wait for element to be visible before screenshotting
    try:
        page.wait_for_selector('#captchaImage', state='visible', timeout=12000)
        return page.locator('#captchaImage').screenshot(timeout=12000)
    except Exception:
        pass
    try:
        page.wait_for_selector('img.image_style', state='visible', timeout=5000)
        return page.locator('img.image_style').screenshot(timeout=8000)
    except Exception:
        return b''


def _parse_title_cell(cell_text: str):
    parts = re.findall(r'\[([^\]]+)\]', cell_text)
    if len(parts) >= 3:
        return parts[0].strip(), parts[1].strip(), parts[2].strip()
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip(), ''
    if len(parts) == 1:
        return parts[0].strip(), '', ''
    return cell_text.strip(), '', ''


def _parse_results_table(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    for table in soup.find_all('table'):
        rows = table.find_all('tr', recursive=False)
        if not rows:
            rows = table.find_all('tr')
        if not rows:
            continue
        header_cells = [td.get_text(' ', strip=True) for td in rows[0].find_all(['td', 'th'])]
        if (
            len(header_cells) >= 5
            and header_cells[0].strip() == 'S.No'
            and 'Published' in header_cells[1]
        ):
            records = []
            for tr in rows[1:]:
                cells = [td.get_text(' ', strip=True) for td in tr.find_all('td')]
                if len(cells) < 5:
                    continue
                if not cells[0].strip().rstrip('.').isdigit():
                    continue
                title_raw = cells[4]
                org = cells[5] if len(cells) > 5 else ''
                title, ref_no, tender_id = _parse_title_cell(title_raw)
                if not title:
                    continue
                records.append({
                    'title': title,
                    'ref_no': ref_no,
                    'tender_id': tender_id,
                    'org': org.split('||')[0].strip(),
                    'published_date': cells[1],
                    'closing_date': cells[2],
                    'opening_date': cells[3],
                })
            return records
    return []


_DETAIL_URL = (
    f'{_PORTAL}?component=$DirectLink'
    '&page=FrontEndTenderDetailNewUi&service=direct&session=T&sp={tender_id}'
)

_DETAIL_FIELDS = [
    'Tender ID', 'Tender Ref. No.', 'Tender Value in ₹', 'Product Category',
    'Sub category', 'Contract Type', 'Bid Validity (Days)', 'Period of Work (Days)',
    'Location', 'Pincode', 'Pre Bid Meeting Place', 'Pre Bid Meeting Address',
    'Pre Bid Meeting Date', 'Bid Opening Place', 'Should Allow NDA Tender',
    'Allow Preferential Bidder', 'Organisation Name', 'Organisation Type',
    'Department Name', 'Office Name', 'Total Tender Value',
    'EMD Amount in ₹', 'EMD Percentage', 'EMD Exemption Allowed',
    'EMD Fee Type', 'Work Description',
]


def _parse_detail_page(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'lxml')
    detail: Dict[str, Any] = {}
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for tr in rows:
            cells = tr.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text(' ', strip=True).rstrip(':').strip()
                value = cells[1].get_text(' ', strip=True)
                if label and value and label in _DETAIL_FIELDS:
                    detail[label] = value
            if len(cells) == 4:
                label2 = cells[2].get_text(' ', strip=True).rstrip(':').strip()
                value2 = cells[3].get_text(' ', strip=True)
                if label2 and value2 and label2 in _DETAIL_FIELDS:
                    detail[label2] = value2
    docs = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        txt = a.get_text(strip=True)
        if any(x in href.lower() for x in ['.pdf', 'document', 'download', 'file']):
            docs.append({'name': txt, 'url': href})
    if docs:
        detail['documents'] = docs
    return detail


def _fetch_tender_detail(page, tender_id: str) -> Dict[str, Any]:
    url = _DETAIL_URL.format(tender_id=tender_id)
    try:
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        page.wait_for_timeout(1000)
        html = page.content()
        return _parse_detail_page(html)
    except Exception as e:
        print(f'  [CPPP] Detail fetch failed for {tender_id}: {e}')
        return {}


def _search_cppp(location: str, headless: bool) -> List[Dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
            )
        )
        page = ctx.new_page()

        for attempt in range(_MAX_CAPTCHA_RETRIES):
            print(f'  [CPPP] Attempt {attempt + 1}/{_MAX_CAPTCHA_RETRIES}...')
            try:
                page.goto(_LOCATION_PAGE, timeout=60000, wait_until='networkidle')
            except Exception as e:
                print(f'  [CPPP] Page load failed: {e}')
                continue

            raw_bytes = _captcha_bytes(page)
            if not raw_bytes:
                print(f'  [CPPP] Could not capture CAPTCHA image, retrying...')
                continue

            cap_text = _solve_captcha(raw_bytes)
            print(f'  [CPPP] CAPTCHA solved as: {cap_text!r}')

            page.fill('input[name=Location]', location)
            page.fill('input[name=captchaText]', cap_text)
            page.press('input[name=captchaText]', 'Enter')
            page.wait_for_timeout(2500)

            body = page.inner_text('body')
            if not cap_text or 'invalid captcha' in body.lower():
                print(f'  [CPPP] Invalid captcha (submitted {cap_text!r}), retrying...')
                continue
            if 'search results for' not in body.lower():
                print(f'  [CPPP] Unexpected response, retrying...')
                continue

            html = page.content()
            rows = _parse_results_table(BeautifulSoup(html, 'lxml'))
            print(f'  [CPPP] Found {len(rows)} tenders — fetching details...')
            for i, row in enumerate(rows):
                tid = row.get('tender_id', '')
                if not tid:
                    continue
                print(f'  [CPPP] Detail {i + 1}/{len(rows)}: {tid}')
                row['detail'] = _fetch_tender_detail(page, tid)
            browser.close()
            return rows

        browser.close()
    return []


def _search_gem(district: str, state: str = 'Uttar Pradesh') -> List[Dict[str, Any]]:
    """Search GeM portal for works/bids in a district via their public API."""
    try:
        resp = requests.get(
            _GEM_SEARCH_URL,
            params={
                'state': state,
                'district': district,
                'category': 'Works',
                'pageNo': 1,
                'pageSize': 50,
            },
            headers=_GEM_HEADERS,
            timeout=30,
        )
        if not resp.ok:
            print(f'  [GEM] API error: {resp.status_code}')
            return _search_gem_portal(district, state)
        data = resp.json()
        items = data.get('bidList') or data.get('data') or data.get('result') or []
        if not isinstance(items, list):
            return _search_gem_portal(district, state)
        rows = []
        for item in items:
            title = item.get('bidTitle') or item.get('title') or item.get('bidName') or ''
            if not title:
                continue
            rows.append({
                'title': title,
                'ref_no': item.get('bidNumber') or item.get('refNo') or '',
                'tender_id': item.get('bidId') or item.get('id') or '',
                'org': item.get('buyerOrganisation') or item.get('org') or '',
                'published_date': item.get('publishedDate') or item.get('startDate') or '',
                'closing_date': item.get('closingDate') or item.get('endDate') or '',
                'opening_date': '',
                'source': 'gem',
            })
        print(f'  [GEM] Found {len(rows)} bids via API')
        return rows
    except Exception as e:
        print(f'  [GEM] API failed ({e}), trying portal scrape...')
        return _search_gem_portal(district, state)


def _search_gem_portal(district: str, state: str = 'Uttar Pradesh') -> List[Dict[str, Any]]:
    """Fallback: scrape gem.gov.in search page for works tenders."""
    try:
        resp = requests.get(
            'https://gem.gov.in/search/bids',
            params={
                'state_name': state,
                'district_name': district,
                'category': 'Works',
            },
            headers={**_GEM_HEADERS, 'Accept': 'text/html'},
            timeout=30,
        )
        if not resp.ok:
            print(f'  [GEM] Portal scrape error: {resp.status_code}')
            return []
        soup = BeautifulSoup(resp.text, 'lxml')
        rows = []
        for card in soup.select('.bid-card, .tender-card, [data-bid-id]'):
            title_el = card.select_one('.bid-title, .title, h3, h4')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                continue
            bid_id = card.get('data-bid-id', '')
            org_el = card.select_one('.org-name, .buyer-name')
            org = org_el.get_text(strip=True) if org_el else ''
            rows.append({
                'title': title,
                'ref_no': bid_id,
                'tender_id': bid_id,
                'org': org,
                'published_date': '',
                'closing_date': '',
                'opening_date': '',
                'source': 'gem',
            })
        print(f'  [GEM] Found {len(rows)} bids via portal scrape')
        return rows
    except Exception as e:
        print(f'  [GEM] Portal scrape failed: {e}')
        return []


# Section 4.2 type weights
_TYPE_WEIGHTS = {
    'highway': 1.00,
    'airport': 1.00,
    'metro': 1.00,
    'expressway': 0.95,
    'railway': 0.90,
    'industrial': 0.85,
    'smart': 0.80,
    'state_highway': 0.75,
    'power_utility': 0.60,
    'water_utility': 0.55,
    'commercial': 0.50,
    'unknown': 0.40,
}

# Org types that signal major infrastructure (Section 3.4)
_INFRA_ORGS = {
    'nhai', 'aai', 'airports authority', 'indian railways', 'railway',
    'pwd', 'public works', 'smart city', 'cpwd', 'rites', 'ircon',
    'nhidcl', 'upeida', 'yeida', 'neda',
}

_DISTRICT_DEFAULT_KM = 15.0  # district-level fallback (covers ~full Ayodhya district)


def _is_infra_org(org: str) -> bool:
    o = org.lower()
    return any(k in o for k in _INFRA_ORGS)


def _geocode_title(title: str, lat: float, lng: float) -> float:
    """Extract place hint from title, geocode it, return distance_km."""
    from ..geo import extract_place_hint, geocode_nominatim, infer_project_distance
    hint = extract_place_hint(title)
    if not hint or len(hint) < 4:
        return _DISTRICT_DEFAULT_KM
    coords = geocode_nominatim(hint)
    if coords:
        return infer_project_distance(lat, lng, coords[0], coords[1])
    return _DISTRICT_DEFAULT_KM


def _compute_distance(row: Dict[str, Any], lat: float, lng: float) -> float:
    """Best-effort distance: detail Location field → title NLP → district default."""
    from ..geo import geocode_nominatim, infer_project_distance
    detail = row.get('detail', {})
    # Try detail page Location / Pincode first (most precise)
    for field in ('Location', 'Pincode'):
        loc_str = detail.get(field, '').strip()
        if loc_str and not loc_str.lower().startswith('uttar pradesh'):
            coords = geocode_nominatim(loc_str)
            if coords:
                return infer_project_distance(lat, lng, coords[0], coords[1])
    # Fall back to NLP on title
    return _geocode_title(row['title'], lat, lng)


def _to_project(row: Dict[str, Any], lat: float, lng: float, district: str = '') -> Dict[str, Any]:
    title = row['title']
    proj_type = classify_tender_type(title)
    detail = row.get('detail', {})
    stage_text = detail.get('Tender Status', '') or row.get('stage', 'open')

    # If tender is confirmed in the subject district, distance decay is not applied.
    tender_district = (detail.get('Location') or '').lower()
    in_district = (
        district.lower() in tender_district
        or row.get('district', '').lower() == district.lower()
        or not tender_district  # no location info → assume district-level → no penalty
    )
    distance_km = 0.0 if in_district else _compute_distance(row, lat, lng)

    return {
        'title': title,
        'ref_no': row['ref_no'],
        'tender_id': row['tender_id'],
        'org': row['org'],
        'source': row.get('source', 'cppp'),
        'type': proj_type,
        'type_weight': _TYPE_WEIGHTS.get(proj_type, 0.40),
        'stage': stage_text or 'open',
        'stage_multiplier': parse_stage(stage_text or 'open'),
        'distance_km': round(distance_km, 2),
        'is_infra_org': _is_infra_org(row['org']),
        'published_date': row.get('published_date', ''),
        'closing_date': row.get('closing_date', ''),
        'opening_date': row.get('opening_date', ''),
        **{k: v for k, v in detail.items() if k not in ('Tender Status',)},
    }


class CpppGemAdapter(PortalAdapter):
    portal_name = 'cppp_gem'
    url = _PORTAL

    def scrape(
        self,
        *,
        lat: float,
        lng: float,
        district: str,
        gatta_number: str | None = None,  # noqa: ARG002  # unused — portal is location-based
        output_dir: Path | None = None,
        headless: bool = True,
    ) -> PortalResult:
        query = {'lat': lat, 'lng': lng, 'district': district}

        cppp_rows = _search_cppp(district, headless)
        gem_rows = _search_gem(district)
        all_rows = cppp_rows + gem_rows

        if not all_rows:
            result = PortalResult(
                self.portal_name, 'EMPTY_PAGE', self.url, query,
                {'infra_projects': []},
                note='No tenders returned from CPPP or GeM (CAPTCHA may have failed)',
            )
            self._save(output_dir, result)
            return result

        infra_projects = [_to_project(row, lat, lng, district) for row in all_rows]

        result = PortalResult(
            self.portal_name, 'OK', self.url, query,
            {'infra_projects': infra_projects, 'total_tenders': len(infra_projects)},
        )
        self._save(output_dir, result)
        return result
