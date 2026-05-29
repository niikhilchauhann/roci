from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import PortalAdapter, PortalResult
from ..geo import geocode_nominatim
from ..utils import haversine_km

_PORTAL = 'https://uprera.azurewebsites.net/View_projects.aspx'
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-IN,en;q=0.9',
    'Referer': _PORTAL,
}

_RADIUS_KM = 5.0
_MAX_PAGES = 10
_MAX_CAPTCHA_RETRIES = 10
_OCR_ALLOWLIST = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

# Section 4.5 — Stage multipliers
_STAGE_MULTIPLIERS = {
    'revoked': -0.30, 'lapsed': -0.30, 'cancelled': -0.30, 'withdrawn': -0.30,
    'completion certificate': 0.60, 'oc obtained': 0.60, 'oc received': 0.60, 'completed': 0.60,
    'under construction': 1.00, 'construction in progress': 1.00, 'construction': 1.00,
    'launched': 0.70, 'under development': 0.70, 'development': 0.70,
}
_DEFAULT_STAGE_MULTIPLIER = 0.50  # Registered / Not launched

# Section 4.5 — Scale weights
_SCALE_LARGE = 1.00   # > 200 units
_SCALE_MEDIUM = 0.80  # 50–200 units
_SCALE_SMALL = 0.60   # < 50 units

_easyocr_reader = None


def _get_ocr():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _easyocr_reader


def _solve_captcha(img_bytes: bytes) -> str:
    """EasyOCR primary; ddddocr fallback."""
    try:
        from PIL import Image, ImageFilter, ImageFile
        import io
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        img = Image.open(io.BytesIO(img_bytes)).convert('L')
        img = img.filter(ImageFilter.MedianFilter(size=3))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        filtered = buf.getvalue()
    except Exception:
        filtered = img_bytes

    try:
        reader = _get_ocr()
        parts = reader.readtext(filtered, detail=0, allowlist=_OCR_ALLOWLIST)
        text = ''.join(parts).strip().replace(' ', '')
        if 4 <= len(text) <= 8 and text.isalnum():
            return text
    except Exception:
        pass

    try:
        import ddddocr
        ocr = ddddocr.DdddOcr(show_ad=False)
        text = ocr.classification(filtered).strip().replace(' ', '')
        if text.isalnum():
            return text.upper()
    except Exception:
        pass

    return ''


def _parse_stage_multiplier(status: str) -> float:
    s = (status or '').lower()
    for kw, mult in _STAGE_MULTIPLIERS.items():
        if kw in s:
            return mult
    return _DEFAULT_STAGE_MULTIPLIER


def _parse_scale_weight(units: int) -> float:
    if units >= 200:
        return _SCALE_LARGE
    if units >= 50:
        return _SCALE_MEDIUM
    return _SCALE_SMALL


def _extract_units_from_name(name: str) -> Optional[int]:
    """Extract unit count from project name, e.g. '314 Nos' or '50 Plots'."""
    m = re.search(r'(\d+)\s*(?:nos?|unit|flat|plot|apartment|dwelling)', name, re.I)
    if m:
        return int(m.group(1))
    return None


def _clean_locality(raw: str) -> str:
    """
    Strip un-geocodable fragments from village/locality strings.
    Removes: Gata/Khasra numbers, PIN codes, parenthetical suffixes,
    road/highway references, and excess punctuation.
    """
    s = raw.strip()
    # Remove "Gata No.", "Khasra No.", plot numbers
    s = re.sub(r'(?i)(gata|khasra|plot|gat|kh\.?)\s*[nN]o\.?\s*[\d/,\s]+', '', s)
    # Remove PIN codes
    s = re.sub(r'\bPIN\s*[-:]?\s*\d{6}\b', '', s, flags=re.I)
    # Remove "Distt-" or "Dist." prefix labels
    s = re.sub(r'\bDistt?\.?\s*[-:]?\s*', '', s, flags=re.I)
    # Strip parenthetical old names e.g. "Sadar(Faizabad)" → "Sadar"
    s = re.split(r'[(*]', s)[0]
    # Remove road/highway fragments that Nominatim misreads as street names
    s = re.sub(r'\b\d+\s*[-–]\s*[Kk]osi\b.*', '', s)
    # Collapse extra whitespace and punctuation
    s = re.sub(r'[\s,]+', ' ', s).strip().strip(',').strip()
    return s


def _build_geocode_query(detail: Dict[str, Any], district: str) -> str:
    """
    Build a geocodable address from detail fields.
    Prefers Village/Locality → Tehsil → District.
    Falls back to project name + district.
    """
    village_raw = detail.get('Village/Locality/Sector', '')
    tehsil_raw = detail.get('Tehsil', '')

    village = _clean_locality(village_raw)
    tehsil = _clean_locality(tehsil_raw)

    parts = [p for p in [village, tehsil, district, 'Uttar Pradesh'] if p]
    if len(parts) >= 3:  # at least village/tehsil + district
        return ', '.join(parts)
    return f'{district}, Uttar Pradesh'


_REG_DATE_PAT = re.compile(r'(UPRERAPRJ\d+)(\d{1,2}/\d{2}/\d{4})')


def _split_reg_date(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    m = _REG_DATE_PAT.match(raw)
    if m:
        return m.group(1), m.group(2)
    return raw, ''


def _parse_promoter_span(span) -> str:
    if span is None:
        return ''
    names = [li.get_text(' ', strip=True) for li in span.find_all('li')]
    return ', '.join(names) if names else span.get_text(' ', strip=True)


def _parse_table(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    table = soup.find('table', id=re.compile(r'GridView', re.I))
    if not table:
        return []

    records = []
    for tr in table.find_all('tr'):
        span = tr.find('span', id=re.compile(r'GridView1_ctl\d+_lbl', re.I))
        if span is None:
            continue
        m = re.search(r'(GridView1_ctl\d+)_lbl', span['id'], re.I)
        prefix = m.group(1) if m else ''

        def _text(lbl: str) -> str:
            tag = tr.find('span', id=re.compile(rf'{prefix}_{lbl}$', re.I))
            return tag.get_text(' ', strip=True) if tag else ''

        raw_reg = _text('lblRegistrationNo')
        reg_number, reg_date = _split_reg_date(raw_reg)
        name = _text('lblProjectName')
        promoter_span = tr.find('span', id=re.compile(rf'{prefix}_lblPromoter$', re.I))
        promoter = _parse_promoter_span(promoter_span)
        district_val = _text('lblDistrict')
        project_type = _text('lblProjectType')
        # Some portals expose status / unit count in additional columns
        status_text = _text('lblStatus') or _text('lblProjectStatus') or ''

        cert_div = tr.find('div', id=re.compile(rf'{prefix}_pnl_file$', re.I))
        cert_url = ''
        if cert_div:
            cert_a = cert_div.find('a', href=True)
            if cert_a:
                href = cert_a['href']
                cert_url = f'https://uprera.azurewebsites.net/{href.lstrip("/")}'

        if not raw_reg and not name:
            continue

        records.append({
            'reg_number': reg_number,
            'reg_date': reg_date,
            'name': name,
            'promoter': promoter,
            'district': district_val,
            'project_type': project_type,
            'status_text': status_text,
            'cert_url': cert_url,
        })
    return records


def _fetch_cert_pdf(session: requests.Session, cert_url: str) -> Dict[str, Any]:
    if not cert_url:
        return {}
    try:
        r = session.get(cert_url, headers=_HEADERS, timeout=30)
        r.raise_for_status()
        if 'pdf' not in r.headers.get('Content-Type', '').lower():
            return {}
        return _parse_cert_pdf(r.content)
    except Exception as e:
        print(f'  [RERA] PDF fetch error: {e}')
        return {}


def _parse_cert_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = '\n'.join(pg.extract_text() or '' for pg in reader.pages)
    except Exception as e:
        print(f'  [RERA] PDF parse error: {e}')
        return {}

    detail: Dict[str, Any] = {}

    def _extract(label: str, text: str) -> str:
        pat = re.compile(rf'{re.escape(label)}\s*[:\-]?\s*(.+?)(?=\n[A-Z]|\Z)', re.S)
        m = pat.search(text)
        return m.group(1).strip().replace('\n', ' ') if m else ''

    for key in ['Village/Locality/Sector', 'Tehsil', 'District/State', 'Proposed Completion Date']:
        val = _extract(key, text)
        if val:
            detail[key] = re.split(r'\n(?=[A-Z][a-z])', val)[0].strip()

    # Extract number of units/plots from cert text
    unit_m = re.search(
        r'(?:Total\s+(?:No\.|Number)\s+of\s+(?:Units|Flats|Plots|Apartments)|'
        r'No\.\s+of\s+(?:Units|Flats|Plots))[:\s]*(\d+)',
        text, re.I
    )
    if unit_m:
        detail['units'] = int(unit_m.group(1))

    # Project status from cert if present
    status_m = re.search(r'Project\s+Status\s*[:\-]?\s*([^\n]+)', text, re.I)
    if status_m:
        detail['status_text'] = status_m.group(1).strip()

    return detail


def _search_with_playwright(district: str, max_pages: int, headless: bool) -> List[Dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    all_rows: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=_HEADERS['User-Agent'],
            viewport={'width': 1280, 'height': 900},
        )
        page = ctx.new_page()

        success = False
        for attempt in range(_MAX_CAPTCHA_RETRIES):
            print(f'  [RERA] Attempt {attempt + 1}/{_MAX_CAPTCHA_RETRIES}...')
            page.goto(_PORTAL, timeout=60000, wait_until='domcontentloaded')
            try:
                page.wait_for_selector('img[src*="CaptchaImage"]', state='visible', timeout=20000)
            except Exception:
                print(f'  [RERA] Attempt {attempt + 1}: captcha image not visible')
                continue

            cap_img = page.locator('img[src*="CaptchaImage"]').first
            try:
                img_bytes = cap_img.screenshot(timeout=12000)
            except Exception:
                print(f'  [RERA] Attempt {attempt + 1}: screenshot failed')
                continue

            cap_text = _solve_captcha(img_bytes)
            print(f'  [RERA] CAPTCHA solved as: {cap_text!r}')

            page.select_option(
                'select[name="ctl00$ContentPlaceHolder1$DdlprojectDistrict"]', district
            )
            page.fill('input[name="ctl00$ContentPlaceHolder1$txtcap"]', cap_text)
            page.click('input[name="ctl00$ContentPlaceHolder1$btnSearch"]')

            try:
                page.wait_for_selector(
                    'table[id*="GridView"] tr td span[id*="lbl"]', timeout=20000
                )
            except Exception:
                body = page.inner_text('body')
                if 'invalid captcha' in body.lower() or 'wrong captcha' in body.lower():
                    print(f'  [RERA] Invalid captcha, retrying...')
                else:
                    print(f'  [RERA] No results on attempt {attempt + 1}')
                continue

            html = page.content()
            rows = _parse_table(BeautifulSoup(html, 'lxml'))
            print(f'  [RERA] Page 1: {len(rows)} rows')
            all_rows.extend(rows)
            success = True
            break

        if not success:
            browser.close()
            return []

        # Paginate
        for pg in range(2, max_pages + 1):
            if len(all_rows) < 10 or len(all_rows) % 10 != 0:
                break
            clicked = False
            for lnk in page.query_selector_all('a'):
                if lnk.inner_text().strip() == str(pg):
                    lnk.click()
                    try:
                        page.wait_for_load_state('networkidle', timeout=15000)
                    except Exception:
                        pass
                    rows = _parse_table(BeautifulSoup(page.content(), 'lxml'))
                    print(f'  [RERA] Page {pg}: {len(rows)} rows')
                    all_rows.extend(rows)
                    clicked = True
                    break
            if not clicked:
                break

        browser.close()
    return all_rows


class ReraUpAdapter(PortalAdapter):
    portal_name = 'rera_up'
    url = _PORTAL

    def scrape(
        self,
        *,
        lat: float,
        lng: float,
        district: str,
        gatta_number: str | None = None,  # noqa: ARG002
        output_dir: Path | None = None,
        headless: bool = True,
        radius_km: float = _RADIUS_KM,
    ) -> PortalResult:
        query = {'lat': lat, 'lng': lng, 'district': district}

        all_raw = _search_with_playwright(district, _MAX_PAGES, headless)

        if not all_raw:
            result = PortalResult(
                self.portal_name, 'EMPTY_PAGE', self.url, query,
                {'rera_projects': []}, note='No rows returned — possible CAPTCHA failure'
            )
            self._save(output_dir, result)
            return result

        session = requests.Session()
        rera_projects: List[Dict[str, Any]] = []

        for i, raw in enumerate(all_raw):
            name = raw.get('name', '').strip()
            reg_number = raw.get('reg_number', '').strip()
            if not name and not reg_number:
                continue

            print(f'  [RERA] Processing {i + 1}/{len(all_raw)}: {reg_number or name}')

            # Fetch PDF cert for address fields + units count
            detail: Dict[str, Any] = {}
            if raw.get('cert_url'):
                detail = _fetch_cert_pdf(session, raw['cert_url'])
                time.sleep(0.3)

            # Unit count: PDF cert → project name → default medium
            units = detail.get('units')
            if units is None:
                units = _extract_units_from_name(name)
            scale_weight = _parse_scale_weight(units) if units is not None else _SCALE_MEDIUM

            # Status: list page → PDF cert → default registered
            status_text = raw.get('status_text') or detail.get('status_text', '')
            stage_multiplier = _parse_stage_multiplier(status_text)

            # Geocode: try progressively simpler queries until one resolves
            village = _clean_locality(detail.get('Village/Locality/Sector', ''))
            tehsil = _clean_locality(detail.get('Tehsil', ''))
            geo_candidates = [
                _build_geocode_query(detail, district),           # full: village, tehsil, district
                f'{village}, {district}, Uttar Pradesh' if village else None,  # village + district only
                f'{village}, Faizabad, Uttar Pradesh' if village else None,    # old district name
                f'{village}, Uttar Pradesh' if village else None,              # minimal
            ]
            coords = None
            for q in geo_candidates:
                if not q:
                    continue
                print(f'  [RERA] Geocoding: {q!r}')
                coords = geocode_nominatim(q)
                if coords:
                    break

            if coords:
                dist_km = haversine_km(lat, lng, coords[0], coords[1])
            else:
                # Still failed — use tehsil as conservative proxy
                tehsil_clean = tehsil.lower()
                if 'sadar' in tehsil_clean:
                    dist_km = 3.0
                    print(f'  [RERA] All geocode attempts failed; Sadar tehsil fallback → {dist_km} km')
                else:
                    dist_km = 10.0
                    print(f'  [RERA] All geocode attempts failed; non-Sadar tehsil fallback → {dist_km} km')

            print(f'  [RERA] Distance: {dist_km:.2f} km (threshold: {radius_km} km)')

            if radius_km is not None and dist_km > radius_km:
                continue

            rera_projects.append({
                # Required by Section 6.6 formula inputs
                'scale_weight': scale_weight,
                'distance_km': round(dist_km, 3),
                'stage_multiplier': stage_multiplier,
                'name': name,
                'reg_number': reg_number,
                # Additional detail fields
                'reg_date': raw.get('reg_date', ''),
                'promoter': raw.get('promoter', ''),
                'project_type': raw.get('project_type', ''),
                'units': units,
                'status_text': status_text or 'registered',
                'village': detail.get('Village/Locality/Sector', ''),
                'tehsil': detail.get('Tehsil', ''),
                'proposed_completion': detail.get('Proposed Completion Date', ''),
                'cert_url': raw.get('cert_url', ''),
                'detail': detail,
            })

        status = 'OK' if rera_projects else 'NO_NEARBY_PROJECTS'
        result = PortalResult(
            self.portal_name, status, self.url, query,
            {
                'rera_projects': rera_projects,
                'total_district_projects': len(all_raw),
            },
        )
        self._save(output_dir, result)
        return result
