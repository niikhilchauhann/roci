from __future__ import annotations

import difflib
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from .base import PortalAdapter, PortalResult

# ── Constants ────────────────────────────────────────────────────────────────

_BASE     = 'https://upbhunaksha.gov.in'
_API      = f'{_BASE}/bhunakshaserver'

_DISTRICT = '177'   # Ayodhya district code (fixed)

_TEHSILS: Dict[str, str] = {
    'bikapur':  '00906',
    'sadar':    '00905',
    'milkipur': '00903',
    'rudauli':  '00902',
    'sohaval':  '00904',
    'sohawal':  '00904',  # alternate spelling
    'ayodhya':  '00905',  # Sadar tehsil is sometimes called Ayodhya
    'faizabad': '00905',  # historic name for same area
}

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
    ),
    'Referer': f'{_BASE}/home',
    'Origin':  _BASE,
}

_NOMINATIM_LAST = 0.0   # module-level throttle


# ── Coordinate conversion ────────────────────────────────────────────────────

def _to_utm44n(lat: float, lng: float) -> Tuple[float, float]:
    """WGS84 → UTM Zone 44N (EPSG:32644). Accurate to ~1 m for UP."""
    a, f = 6378137.0, 1 / 298.257223563
    b    = a * (1 - f)
    e2   = 1 - (b / a) ** 2
    lon0 = math.radians(81.0)
    la, lo = math.radians(lat), math.radians(lng)
    N  = a / math.sqrt(1 - e2 * math.sin(la) ** 2)
    T  = math.tan(la) ** 2
    C  = e2 / (1 - e2) * math.cos(la) ** 2
    A  = math.cos(la) * (lo - lon0)
    M  = a * (
        (1 - e2 / 4 - 3 * e2 ** 2 / 64) * la
        - (3 * e2 / 8 + 3 * e2 ** 2 / 32) * math.sin(2 * la)
        + (15 * e2 ** 2 / 256) * math.sin(4 * la)
    )
    k0 = 0.9996
    x  = k0 * N * (A + (1 - T + C) * A ** 3 / 6) + 500_000
    y  = k0 * (M + N * math.tan(la) * (A ** 2 / 2 + (5 - T + 9 * C) * A ** 4 / 24))
    return x, y


# ── Reverse geocoding ────────────────────────────────────────────────────────

def _reverse_geocode(lat: float, lng: float) -> Dict[str, str]:
    """
    Nominatim reverse geocode → returns address dict.
    Relevant keys: village, suburb, county, state_district.
    """
    global _NOMINATIM_LAST
    gap = time.monotonic() - _NOMINATIM_LAST
    if gap < 1.0:
        time.sleep(1.0 - gap)
    _NOMINATIM_LAST = time.monotonic()

    try:
        r = requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={'lat': lat, 'lon': lng, 'format': 'json', 'zoom': 16,
                    'addressdetails': 1},
            headers={'User-Agent': 'roci-engine/0.1'},
            timeout=10,
        )
        if r.ok:
            return r.json().get('address', {})
    except Exception as e:
        print(f'  [Bhunaksha] Nominatim error: {e}')
    return {}


def _pick_tehsil(address: Dict[str, str]) -> str:
    """Map Nominatim address fields to an Ayodhya tehsil code."""
    # Nominatim returns tehsil in 'county' or 'state_district' for UP
    candidates = [
        address.get('county', ''),
        address.get('state_district', ''),
        address.get('suburb', ''),
        address.get('city_district', ''),
    ]
    for cand in candidates:
        key = cand.lower().strip()
        if key in _TEHSILS:
            return _TEHSILS[key]
        # Partial match
        for name, code in _TEHSILS.items():
            if name in key or key in name:
                return code
    # Default to Sadar (central Ayodhya city tehsil)
    print('  [Bhunaksha] Could not determine tehsil from geocode — defaulting to Sadar')
    return _TEHSILS['sadar']


# ── Portal API helpers ───────────────────────────────────────────────────────

def _get_villages(tehsil_code: str) -> List[Dict[str, Any]]:
    """
    POST /masterdata/levelvalue with level=3 (village) and district+tehsil codes.
    Returns a list of village objects.
    """
    s = requests.Session()
    s.headers.update(_HEADERS)
    r = s.post(
        f'{_API}/masterdata/levelvalue',
        data={'level': '3', 'codes': f'{_DISTRICT},{tehsil_code}'},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    # Handle both list response and {"data": [...]} envelope
    if isinstance(data, list):
        return data
    return data.get('data', data.get('villages', []))


def _match_village(villages: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """
    Fuzzy-match a Nominatim village name against the portal's village list.
    Returns the best-matching village dict, or None.
    """
    if not villages or not name:
        return None

    # Discover the name key (commonly 'name', 'villageName', 'value', 'label')
    sample = villages[0]
    name_key = next((k for k in ('name', 'villageName', 'value', 'label', 'NAME')
                     if k in sample), None)
    code_key = next((k for k in ('code', 'villageCode', 'id', 'CODE')
                     if k in sample), None)

    if not name_key or not code_key:
        print(f'  [Bhunaksha] Unrecognised village list schema: {sample}')
        return None

    portal_names = [str(v[name_key]).lower() for v in villages]
    query = name.lower()
    matches = difflib.get_close_matches(query, portal_names, n=1, cutoff=0.5)
    if matches:
        idx = portal_names.index(matches[0])
        return villages[idx]

    return None


def _get_plot_at_xy(giscode: str, x: float, y: float) -> Dict[str, Any]:
    """
    POST getPlotAtXY → returns the plot/khasra info for the UTM coordinate.
    """
    s = requests.Session()
    s.headers.update(_HEADERS)
    r = s.post(
        f'{_API}/MapInfo/getPlotAtXY',
        data={'giscode': giscode, 'x': str(x), 'y': str(y), 'plotno': 'undefined'},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _get_plot_info(giscode: str, plot_no: str) -> Dict[str, Any]:
    """
    POST getPlotInfo → full plot details for a known giscode + plot number.
    """
    s = requests.Session()
    s.headers.update(_HEADERS)
    r = s.post(
        f'{_API}/MapInfo/getPlotInfo',
        json={'gisCode': giscode, 'plotNo': plot_no},
        headers={**_HEADERS, 'Content-Type': 'application/json'},
        timeout=20,
    )
    r.raise_for_status()
    # Response is text/plain but contains JSON
    try:
        return r.json()
    except Exception:
        return {'raw': r.text}


def _extract_khasra(plot_response: Dict[str, Any]) -> str:
    """Pull the khasra/plot number out of getPlotAtXY response."""
    for key in ('plotNo', 'plot_no', 'khasraNo', 'khasra_no', 'PLOT_NO', 'KHASRA_NO', 'kide'):
        val = plot_response.get(key)
        if val and str(val).strip() not in ('', 'undefined', 'null'):
            return str(val).strip()
    return ''


def _extract_giscode(plot_response: Dict[str, Any]) -> str:
    """Pull the giscode out of a getPlotAtXY response (bhucode / gisCode / giscode)."""
    for key in ('bhucode', 'gisCode', 'giscode', 'GIS_CODE'):
        val = plot_response.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return ''


# ── Parallel village search ──────────────────────────────────────────────────

def _search_all_tehsils(x: float, y: float, max_workers: int = 30) -> Optional[Dict[str, Any]]:
    """
    Fetch village lists for all 5 Ayodhya tehsils, then fire getPlotAtXY
    concurrently across every village with hasData=true.
    Returns the first hit, or None if no village contains the point.
    """
    unique_tehsils = list(dict.fromkeys(_TEHSILS.values()))  # preserve insertion order, dedupe

    # Collect all (tehsil_code, village) pairs with hasData=true
    all_candidates: List[tuple] = []
    for tehsil_code in unique_tehsils:
        try:
            villages = _get_villages(tehsil_code)
            for v in villages:
                if v.get('extraParams', {}).get('hasData'):
                    all_candidates.append((tehsil_code, v))
        except Exception as e:
            print(f'  [Bhunaksha] Village fetch error for tehsil {tehsil_code}: {e}')

    if not all_candidates:
        return None

    print(f'  [Bhunaksha] Searching {len(all_candidates)} villages across all tehsils (workers={max_workers})...')

    def probe(tehsil_code: str, village: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        code_key = next((k for k in ('code', 'villageCode', 'id', 'CODE') if k in village), None)
        if not code_key:
            return None
        giscode = f'{_DISTRICT}{tehsil_code}{village[code_key]}'
        try:
            resp = _get_plot_at_xy(giscode, x, y)
            if resp and _extract_khasra(resp):
                return {**resp, '_giscode': giscode, '_village': village}
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(probe, tc, v): (tc, v) for tc, v in all_candidates}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                for f in futures:
                    f.cancel()
                return result

    return None


# ── Playwright fallback ──────────────────────────────────────────────────────

def _mat_select(page, selector: str, value_hint: str) -> bool:
    """Click a mat-select and choose the option whose text contains value_hint."""
    try:
        page.click(selector, timeout=5000)
        page.wait_for_selector('mat-option', state='visible', timeout=5000)
        for opt in page.query_selector_all('mat-option'):
            if value_hint in (opt.inner_text() or ''):
                opt.click()
                return True
    except Exception as e:
        print(f'  [Bhunaksha] mat-select {selector} ({value_hint}): {e}')
    return False


def _playwright_get_plot(lat: float, lng: float, tehsil_code: str, headless: bool) -> Dict[str, Any]:
    """
    Drive the Bhunaksha portal:
      1. Select district Ayodhya (177) and the given tehsil via mat-select dropdowns.
      2. Collect WMS tile BBOXes to determine viewport extent and resolution.
      3. Calculate the pixel position for (lat, lng) and click it.
      4. Intercept the getPlotAtXY POST response.
    """
    from playwright.sync_api import sync_playwright
    from urllib.parse import parse_qs, urlparse

    x_utm, y_utm = _to_utm44n(lat, lng)
    tiles: List[Dict[str, float]] = []
    captured: Dict[str, Any] = {}

    def on_request(req):
        if 'WMS/tile' in req.url and 'BBOX' in req.url:
            qs = parse_qs(urlparse(req.url).query)
            bbox = qs.get('BBOX', [''])[0].split(',')
            if len(bbox) == 4:
                tiles.append({
                    'minx': float(bbox[0]), 'miny': float(bbox[1]),
                    'maxx': float(bbox[2]), 'maxy': float(bbox[3]),
                    'w': int(qs.get('WIDTH', ['256'])[0]),
                    'h': int(qs.get('HEIGHT', ['256'])[0]),
                })

    def on_response(resp):
        if 'getPlotAtXY' in resp.url and resp.status == 200:
            try:
                j = resp.json()
                if j:
                    captured['plot'] = j
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_context(user_agent=_HEADERS['User-Agent']).new_page()
        page.on('request', on_request)
        page.on('response', on_response)

        try:
            page.goto(f'{_BASE}/home', timeout=60_000, wait_until='networkidle')
            page.wait_for_timeout(2000)
            tiles.clear()   # discard pre-load tiles; only capture post-selection

            # Select district Ayodhya (177)
            ok = _mat_select(page, '#mat-select-0', '177')
            print(f'  [Bhunaksha] District select: {ok}')
            page.wait_for_timeout(2000)

            # Select tehsil
            ok = _mat_select(page, '#mat-select-2', tehsil_code)
            print(f'  [Bhunaksha] Tehsil select: {ok}')
            page.wait_for_timeout(3000)   # let tiles load

            print(f'  [Bhunaksha] Tiles captured: {len(tiles)}')

            if tiles:
                # Compute viewport extent (union of all tile BBOXes)
                vp_minx = min(t['minx'] for t in tiles)
                vp_maxx = max(t['maxx'] for t in tiles)
                vp_miny = min(t['miny'] for t in tiles)
                vp_maxy = max(t['maxy'] for t in tiles)
                # Resolution (m per pixel) from any tile
                res = (tiles[0]['maxx'] - tiles[0]['minx']) / tiles[0]['w']
                print(f'  [Bhunaksha] Viewport UTM: x={vp_minx:.0f}..{vp_maxx:.0f}  y={vp_miny:.0f}..{vp_maxy:.0f}  res={res:.2f}m/px')
                print(f'  [Bhunaksha] Target UTM:  x={x_utm:.0f}  y={y_utm:.0f}')

                # Map div starts at y=28 in page coords (from earlier measurement)
                MAP_TOP = 28.15625
                cx = (x_utm - vp_minx) / res
                cy = MAP_TOP + (vp_maxy - y_utm) / res

                print(f'  [Bhunaksha] Click pixel: cx={cx:.0f}  cy={cy:.0f}')

                if 0 <= cx <= 1280 and MAP_TOP <= cy <= MAP_TOP + 720:
                    page.mouse.click(cx, cy)
                    page.wait_for_timeout(2500)
                else:
                    print('  [Bhunaksha] Target pixel outside viewport — falling back to center click')
                    page.mouse.click(640, MAP_TOP + 360)
                    page.wait_for_timeout(2500)
            else:
                # No tiles captured — try clicking map center anyway
                page.mouse.click(640, 28 + 360)
                page.wait_for_timeout(2500)

        except Exception as e:
            print(f'  [Bhunaksha] Playwright error: {e}')
        finally:
            browser.close()

    return captured.get('plot', {})


# ── Adapter ──────────────────────────────────────────────────────────────────

class BhunakshaAdapter(PortalAdapter):
    portal_name = 'bhunaksha'
    url = _BASE

    def scrape(
        self,
        *,
        lat: float,
        lng: float,
        district: str,           # noqa: ARG002 (Ayodhya only)
        gatta_number: str | None = None,  # noqa: ARG002
        output_dir: Path | None = None,
        headless: bool = True,
    ) -> PortalResult:
        query = {'lat': lat, 'lng': lng, 'district': 'Ayodhya'}

        def _decimal_places(v: float) -> int:
            s = f'{v:.10f}'.rstrip('0')
            return len(s.split('.')[1]) if '.' in s else 0

        for name, val in (('lat', lat), ('lng', lng)):
            if _decimal_places(val) < 6:
                print(
                    f'  [Bhunaksha] WARNING: {name}={val} has fewer than 6 decimal places. '
                    f'Provide at least 6 decimal places (e.g. {val:.6f}) for plot-level precision.'
                )

        try:
            x, y = _to_utm44n(lat, lng)

            # --- Path A: reverse geocode → village match → getPlotAtXY ---
            print('  [Bhunaksha] Reverse geocoding...')
            address = _reverse_geocode(lat, lng)
            print(f'  [Bhunaksha] Address: {address}')
            tehsil_code = _pick_tehsil(address)
            print(f'  [Bhunaksha] Tehsil code: {tehsil_code}')

            villages = _get_villages(tehsil_code)
            print(f'  [Bhunaksha] {len(villages)} villages found')

            village_name = (
                address.get('village') or address.get('hamlet') or address.get('suburb') or ''
            )
            village = _match_village(villages, village_name)
            giscode: str | None = None

            if village:
                code_key = next((k for k in ('code', 'villageCode', 'id', 'CODE')
                                 if k in village), None)
                if code_key:
                    village_code = str(village[code_key])
                    giscode = f'{_DISTRICT}{tehsil_code}{village_code}'
                    print(f'  [Bhunaksha] Matched village → giscode: {giscode}')
                    plot_resp = _get_plot_at_xy(giscode, x, y)
                    print(f'  [Bhunaksha] getPlotAtXY: {plot_resp}')
                    khasra_number = _extract_khasra(plot_resp)
                    if khasra_number:
                        plot_info = _get_plot_info(giscode, khasra_number)
                        data = {
                            'khasra_number': khasra_number,
                            'giscode': giscode,
                            'village_name': village_name,
                            'plot_info': plot_info,
                        }
                        result = PortalResult(self.portal_name, 'OK', self.url, query, data)
                        self._save(output_dir, result)
                        return result

            # --- Path B: parallel village search across all tehsils ---
            print('  [Bhunaksha] Village name match failed — searching all tehsils in parallel...')
            match = _search_all_tehsils(x, y)
            if match:
                giscode = match.pop('_giscode')
                matched_village = match.pop('_village')
                khasra_number = _extract_khasra(match)
                # Server may return bhucode as the authoritative giscode
                giscode = _extract_giscode(match) or giscode
                plot_info = _get_plot_info(giscode, khasra_number)
                data = {
                    'khasra_number': khasra_number,
                    'giscode': giscode,
                    'village_name': str(matched_village.get('value', '')),
                    'village_code': str(matched_village.get(
                        next((k for k in ('code', 'villageCode', 'id') if k in matched_village), ''), ''
                    )),
                    'plot_info': plot_info,
                }
                result = PortalResult(self.portal_name, 'OK', self.url, query, data)
                self._save(output_dir, result)
                return result

            # --- Path C: Playwright intercept (last resort) ---
            print('  [Bhunaksha] Parallel search failed — trying Playwright...')
            plot_resp = _playwright_get_plot(lat, lng, tehsil_code, headless)
            print(f'  [Bhunaksha] Playwright getPlotAtXY: {plot_resp}')
            khasra_number = _extract_khasra(plot_resp)

            if khasra_number:
                giscode = _extract_giscode(plot_resp) or giscode or ''
                plot_info = _get_plot_info(giscode, khasra_number) if giscode else {}
                data = {
                    'khasra_number': khasra_number,
                    'giscode': giscode,
                    'village_name': village_name,
                    'plot_info': plot_info,
                }
                result = PortalResult(self.portal_name, 'OK', self.url, query, data)
            else:
                result = PortalResult(self.portal_name, 'EMPTY_PAGE', self.url, query,
                                      {'khasra_number': None},
                                      note='Could not resolve khasra via village match or Playwright')

        except Exception as e:
            result = PortalResult(self.portal_name, 'ERROR', self.url, query,
                                  {'khasra_number': None}, note=str(e))

        self._save(output_dir, result)
        return result
