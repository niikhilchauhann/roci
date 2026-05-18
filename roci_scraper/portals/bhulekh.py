from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import PortalAdapter, PortalResult

class BhulekhAdapter(PortalAdapter):
    portal_name = 'bhulekh'
    url = 'https://upbhulekh.gov.in'

    def scrape(self, *, lat: float, lng: float, district: str, gatta_number: str | None = None, output_dir: Path | None = None, headless: bool = True) -> PortalResult:
        query = {'lat': lat, 'lng': lng, 'district': district, 'gatta_number': gatta_number}
        try:
            snap, blocker = self._snapshot(self.url, headless=headless)
        except Exception as e:
            result = PortalResult(self.portal_name, 'ERROR', self.url, query, {}, note=str(e))
            self._save(output_dir, result)
            return result

        if blocker:
            result = PortalResult(self.portal_name, 'CAPTCHA_REQUIRED', self.url, query, {'reason': blocker}, note='Blocked at landing page')
            self._save(output_dir, result)
            return result

        data = self._generic_parse(snap.html, snap.text, ['खतौनी', 'bhulekh', 'भूमि', 'प्रकार', 'mutation', 'दाखिल', 'खारिज'])
        text = snap.text
        # Heuristic parsing for mutation and Bhoomi Prakar from visible text/table cells.
        import re
        low = text.lower()
        if any(k in low for k in ['स्वीकृत', 'swikriti', 'approved', 'clear']):
            data['mutation_status'] = 'CLEAR'
        elif any(k in low for k in ['प्रक्रियाधीन', 'pending']):
            data['mutation_status'] = 'PENDING'
        elif any(k in low for k in ['आपत्ति', 'disputed']):
            data['mutation_status'] = 'DISPUTED'
        else:
            data['mutation_status'] = 'UNKNOWN'

        # Parse likely Bhoomi Prakar field values from key/value lines
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if any(k in line.lower() for k in ['भूमि प्रकार', 'bhoomi prakar', 'land type', 'प्रकार']):
                parts = re.split(r'[:：-]', line, maxsplit=1)
                if len(parts) > 1:
                    data['bhoomi_prakar'] = parts[1].strip()
                    break
        if gatta_number:
            data['gatta_number'] = gatta_number
        result = PortalResult(self.portal_name, 'OK' if (data['table_records'] or data['key_values']) else 'EMPTY_PAGE', self.url, query, data)
        self._save(output_dir, result)
        return result
