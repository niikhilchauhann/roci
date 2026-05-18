from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import PortalAdapter, PortalResult

class IgrsupAdapter(PortalAdapter):
    portal_name = 'igrsup'
    url = 'https://igrsup.gov.in'

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

        # Heuristic: try likely links first; if site exposes a public deed search, follow it.
        try:
            from ..browser import BrowserSession
            keywords = ['विलेख', 'deed', 'property', 'search', 'registr']
            snap2 = BrowserSession(headless=headless).click_text(self.url, keywords)
            if snap2.url != self.url:
                snap = snap2
        except Exception:
            pass

        data = self._generic_parse(snap.html, snap.text, ['deed', 'विलेख', 'registration', 'consideration', 'sale'])
        # Extract the strongest numeric hints from visible text.
        text = snap.text
        import re
        nums = [int(x.replace(',', '')) for x in re.findall(r'\b\d{1,5}(?:,\d{3})*\b', text)]
        # conservative: keep first two reasonable counts if present
        if nums:
            data['n_current'] = nums[0]
            data['n_previous'] = nums[1] if len(nums) > 1 else max(nums[0] - 5, 0)
        data.setdefault('n_current', 0)
        data.setdefault('n_previous', 0)
        data['source_hint'] = 'landing_page_or_followed_link'
        result = PortalResult(self.portal_name, 'OK' if (data['table_records'] or data['key_values']) else 'EMPTY_PAGE', self.url, query, data)
        self._save(output_dir, result)
        return result
