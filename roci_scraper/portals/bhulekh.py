from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from ..normalize import _lookup_mapping as _clu_lookup

from .base import PortalAdapter, PortalResult
from .bhunaksha import (
    _to_utm44n,
    _search_all_tehsils,
)

# ── AES outer layer (same key used by upbhulekh.gov.in Angular app) ──────────
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

_AES_KEY = b'12345678901234567890123456789012'
_AES_IV  = b'1234567890123456'

# Tehsil code → English name fragment as shown in bhulekh table
_TEHSIL_DISPLAY: Dict[str, str] = {
    '00905': 'Faizabad',   # Sadar / Faizabad
    '00906': 'Bikapur',
    '00903': 'Milkipur',
    '00902': 'Rudauli',
    '00904': 'Sohwal',
}


def _outer_decrypt(b64str: str) -> Any:
    if not _HAS_CRYPTO:
        return None
    try:
        ct  = base64.b64decode(b64str + '==')
        raw = AES.new(_AES_KEY, AES.MODE_CBC, _AES_IV).decrypt(ct)
        return json.loads(unpad(raw, 16).decode())
    except Exception:
        return None


def _khasra_digits(gatta_number: str) -> str:
    """Extract the leading integer from a gatta like '374/1-A' → '374'."""
    m = re.match(r'(\d+)', gatta_number.strip())
    return m.group(1) if m else ''


def _parse_mutation_status(ror: Dict[str, Any]) -> str:
    """
    Infer mutation status from the /api/ror payload.

    lr_payblexDTOs  → pending revenue litigation → DISPUTED
    specialOrder    → pending order/mutation     → PENDING
    otherwise       → CLEAR
    """
    if ror.get('lr_payblexDTOs'):
        return 'TAX_DUES'
    if ror.get('specialOrder'):
        return 'PENDING'
    return 'CLEAR'


def _extract_khatauni_text(page_text: str) -> str:
    """Trim boilerplate headers/footers, return the core khatauni record text."""
    start = page_text.find('District :')
    if start == -1:
        start = page_text.find('Khata Number')
    end = page_text.find('Disclaimer:')
    if start == -1:
        return page_text.strip()
    return page_text[start:end].strip() if end > start else page_text[start:].strip()


def _parse_land_type_desc(page_text: str, land_descs: List[Dict]) -> str:
    """Extract English land type description from the switched page text."""
    m = re.search(r'Land Type\s*:\s*[\w-]+/(.+)', page_text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Fallback: return the Hindi desc from the API
    return land_descs[0].get('land_type_desc', '') if land_descs else ''


def _parse_owners_from_page(page_text: str) -> List[str]:
    """Extract owner names from the English uddharan page text."""
    owners: List[str] = []
    # After the language switch the owner cell looks like:
    #   "1) Ram Kumar / Shyam Lal / Village"
    # We collect lines that start with a digit+) pattern in the khatedar section.
    in_section = False
    for line in page_text.splitlines():
        line = line.strip()
        if 'Khatedar Ka Vivaran' in line or 'Khatedar' in line:
            in_section = True
        if in_section and re.match(r'\d+\)', line):
            # Strip the index prefix and trailing address parts
            parts = line.split('/')
            name = parts[0].strip().lstrip('0123456789) ').strip()
            if name and name.lower() not in ('', '-', '.'):
                owners.append(name)
        if in_section and 'Kul' in line and 'Kshetrafal' in line:
            break
    return owners


def _parse_owners(ror: Dict[str, Any]) -> List[str]:
    raw = ror.get('names') or []
    if isinstance(raw, list):
        return [str(n) for n in raw if n]
    if isinstance(raw, str):
        return [raw]
    return []


class BhulekhAdapter(PortalAdapter):
    portal_name = 'bhulekh'
    url = 'https://upbhulekh.gov.in'

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
        query = {'lat': lat, 'lng': lng, 'district': district, 'gatta_number': gatta_number}

        # Validate inputs ────────────────────────────────────────────────────
        if not gatta_number:
            result = PortalResult(self.portal_name, 'ERROR', self.url, query, {},
                                  note='gatta_number required for bhulekh lookup')
            self._save(output_dir, result)
            return result

        khasra_str = _khasra_digits(gatta_number)
        if not khasra_str:
            result = PortalResult(self.portal_name, 'ERROR', self.url, query, {},
                                  note=f'Cannot extract khasra digits from gatta_number={gatta_number!r}')
            self._save(output_dir, result)
            return result

        # Locate village via bhunaksha spatial search (parallel probe across all tehsils)
        try:
            x, y = _to_utm44n(lat, lng)
            hit  = _search_all_tehsils(x, y)
        except Exception as exc:
            result = PortalResult(self.portal_name, 'ERROR', self.url, query, {},
                                  note=f'Village lookup failed: {exc}')
            self._save(output_dir, result)
            return result

        if not hit:
            result = PortalResult(self.portal_name, 'EMPTY_PAGE', self.url, query, {},
                                  note='No bhunaksha village found for these coordinates')
            self._save(output_dir, result)
            return result

        village_meta   = hit.get('_village', {})
        village_eng    = village_meta.get('vname_eng', '')
        tehsil_code    = hit.get('_giscode', '177' + '00905')[3:8]  # chars 3-7 = tehsil code
        tehsil_display = _TEHSIL_DISPLAY.get(tehsil_code, 'Faizabad')

        # Playwright navigation ───────────────────────────────────────────────
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            result = PortalResult(self.portal_name, 'ERROR', self.url, query, {},
                                  note='playwright not installed')
            self._save(output_dir, result)
            return result

        try:
            data = self._run_playwright(
                district=district,
                tehsil_display=tehsil_display,
                village_eng=village_eng,
                khasra_str=khasra_str,
                gatta_number=gatta_number,
                headless=headless,
            )
        except Exception as exc:
            result = PortalResult(self.portal_name, 'ERROR', self.url, query, {},
                                  note=str(exc))
            self._save(output_dir, result)
            return result

        status = 'OK' if data else 'EMPTY_PAGE'
        result = PortalResult(self.portal_name, status, self.url, query, data)
        self._save(output_dir, result)
        return result

    # ── internal Playwright session ──────────────────────────────────────────

    def _run_playwright(
        self,
        *,
        district: str,
        tehsil_display: str,
        village_eng: str,
        khasra_str: str,
        gatta_number: str,
        headless: bool,
    ) -> Dict[str, Any]:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        captured: Dict[str, Any] = {}

        def _on_response(resp) -> None:
            url = resp.url
            if '/api/' not in url:
                return
            try:
                body  = json.loads(resp.body())
                edata = body.get('edata', '')
                if edata:
                    dec = _outer_decrypt(edata)
                    if dec is not None:
                        key = url.split('/api/')[-1].split('?')[0]
                        captured[key] = dec
            except Exception:
                pass

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            page    = browser.new_page()
            page.on('response', _on_response)

            # Step 1 – home → card-1 (sets serviceType so village click routes correctly)
            page.goto(f'{self.url}/#/home', wait_until='networkidle', timeout=60_000)
            page.wait_for_timeout(2_000)
            page.locator('.card.card-hover.card-1').click()
            page.wait_for_timeout(2_000)

            # Step 2 – select district
            page.locator('table').nth(0).locator(f'tr:has-text("{district}")').click()
            page.wait_for_timeout(3_000)

            # Step 3 – select tehsil (match on English name fragment)
            page.locator('table').nth(1).locator(
                f'tr:has-text("{tehsil_display}")'
            ).first.click()
            page.wait_for_timeout(3_000)

            # Step 4 – select village (iterate rows for best match)
            village_rows = page.locator('table').nth(2).locator('tr').all()
            clicked_village = False
            for row in village_rows:
                txt = row.inner_text()
                if village_eng.lower() in txt.lower():
                    row.click()
                    clicked_village = True
                    break

            if not clicked_village and village_rows:
                # Fallback: click first row
                village_rows[0].click()

            page.wait_for_timeout(5_000)

            if 'khatauni_rtk' not in page.url:
                browser.close()
                raise RuntimeError(
                    f'Navigation to khatauni_rtk failed (url={page.url}); '
                    f'village={village_eng!r} tehsil={tehsil_display!r}'
                )

            # Step 5 – enter khasra digits via virtual keyboard
            for digit in khasra_str:
                page.locator(f'a.thCellChild[data-value="{digit}"]').first.click()
                page.wait_for_timeout(150)

            # Step 6 – enable and click the first खोजें button (khasra search)
            page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                const b = btns.find(b => b.innerText.includes('खोजें')
                                     && !b.innerText.includes('उद्धरण'));
                if (b) { b.removeAttribute('disabled'); b.click(); }
            }
            """)
            page.wait_for_timeout(5_000)

            # Check for "No Data Found" alert
            alert = page.evaluate("""
            () => {
                const p = document.querySelector('.swal2-popup');
                if (!p || !p.offsetParent) return null;
                return document.querySelector('.swal2-title')?.innerText || 'alert';
            }
            """)
            if alert:
                browser.close()
                return {}   # no records → EMPTY_PAGE

            unique_codes: List[Dict] = captured.get('uniqueCode', [])
            if not unique_codes:
                browser.close()
                return {}

            # Step 7 – pick the best matching khasra sub-entry
            # Prefer exact gatta match (e.g. "374/1-A" → "374/1-A" or "374क")
            # Fall back to first entry
            target = unique_codes[0]
            for uc in unique_codes:
                kno = str(uc.get('khasra_no', ''))
                if gatta_number in kno or kno in gatta_number:
                    target = uc
                    break

            # Step 8 – click result item then उद्धरण देखें
            khasra_label = target.get('khasra_no', '')
            matching_elems = page.locator(f'text={khasra_label}').all()
            if matching_elems:
                matching_elems[0].click()
                page.wait_for_timeout(1_500)

            page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                const b = btns.find(b => b.innerText.includes('उद्धरण देखें'));
                if (b) { b.removeAttribute('disabled'); b.click(); }
            }
            """)
            page.wait_for_timeout(8_000)

            # Step 9 – switch to English so page text is readable
            try:
                page.select_option('select', value='en_in')
                page.wait_for_timeout(2_000)
            except Exception:
                pass

            page_text = page.inner_text('body')
            browser.close()

        ror: Dict[str, Any] = captured.get('ror', {})
        if not ror:
            return {}

        land_descs: List[Dict] = ror.get('landDesc') or []
        bhoomi_prakar = land_descs[0]['land_type'] if land_descs else ''
        bhoomi_prakar_desc = _parse_land_type_desc(page_text, land_descs)
        owner_names = _parse_owners_from_page(page_text) or _parse_owners(ror)
        ref_dir = Path(__file__).resolve().parent.parent / 'ref_data'
        clu_current = _clu_lookup(bhoomi_prakar, ref_dir)
        khatauni_text = _extract_khatauni_text(page_text)

        data: Dict[str, Any] = {
            'gatta_number':       gatta_number,
            'khasra_no':          target.get('khasra_no', ''),
            'khata_number':       target.get('khata_number', ''),
            'area_ha':            target.get('area', ''),
            'bhoomi_prakar':      bhoomi_prakar,
            'bhoomi_prakar_desc': bhoomi_prakar_desc,
            'clu_current':        clu_current,
            'mutation_status':    _parse_mutation_status(ror),
            'owner_names':        owner_names,
            'khatauni_text':      khatauni_text,
            'unique_code':        target.get('unique_code', ''),
            'all_khasras':        [u.get('khasra_no') for u in unique_codes],
        }
        return data
