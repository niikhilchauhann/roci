from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import PortalAdapter, PortalResult

class BhunakshaAdapter(PortalAdapter):
    portal_name = 'bhunaksha'
    url = 'https://bhunaksha.up.gov.in'

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

        data = self._generic_parse(snap.html, snap.text, ['gatta', 'khasra', 'parcel', 'plot', 'भू', 'नक्शा', 'map'])
        # Attempt to detect WFS/WMS hints from page scripts.
        import re
        scripts = re.findall(r'(https?://[^\s"\']+|/[^\s"\']+)', snap.html)
        wfs = next((u for u in scripts if 'wfs' in u.lower() or 'ows' in u.lower()), None)
        if wfs:
            data['wfs_hint'] = wfs
        if gatta_number:
            data['gatta_number'] = gatta_number
        result = PortalResult(self.portal_name, 'OK' if (data['table_records'] or data['key_values'] or data.get('wfs_hint')) else 'EMPTY_PAGE', self.url, query, data)
        self._save(output_dir, result)
        return result
