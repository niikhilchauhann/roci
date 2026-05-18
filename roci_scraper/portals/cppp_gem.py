from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import PortalAdapter, PortalResult
from ..geo import classify_tender_type, extract_place_hint, parse_stage
from ..utils import haversine_km

class CpppGemAdapter(PortalAdapter):
    portal_name = 'cppp_gem'
    url = 'https://eprocure.gov.in/eprocure/app'

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

        data = self._generic_parse(snap.html, snap.text, ['tender', 'bid', 'estimated value', 'stage', 'published', 'award', 'work order'])
        projects = []
        # Reuse extracted table rows if present; otherwise try to mine visible text for tender-like rows.
        rows = data.get('table_records', [])
        for row in rows[:25]:
            joined = ' '.join(str(v) for v in row.values())
            if not joined.strip():
                continue
            title = str(row.get('Tender Title') or row.get('Title') or row.get('Tender') or row.get('Description') or joined[:200])
            stage = str(row.get('Stage') or row.get('Status') or row.get('Procurement Stage') or '')
            org = str(row.get('Organisation') or row.get('Organization') or row.get('Dept') or row.get('Department') or '')
            proj_type = classify_tender_type(title)
            scale = parse_stage(stage)
            projects.append({
                'type': proj_type,
                'stage': stage,
                'stage_multiplier': scale,
                'title': title,
                'org': org,
                'distance_km': 999.0,
                'type_weight': {
                    'highway': 1.0, 'airport': 1.0, 'metro': 1.0, 'expressway': 0.95,
                    'railway': 0.90, 'industrial': 0.85, 'smart': 0.80, 'state_highway': 0.75, 'utility': 0.60
                }.get(proj_type, 0.40),
            })
        if not projects and snap.text:
            lines = [l.strip() for l in snap.text.splitlines() if l.strip()]
            for line in lines[:40]:
                if any(k in line.lower() for k in ['tender', 'bid', 'work order', 'loa', 'published']):
                    projects.append({
                        'type': classify_tender_type(line),
                        'stage': line,
                        'stage_multiplier': parse_stage(line),
                        'title': line[:220],
                        'org': '',
                        'distance_km': 999.0,
                        'type_weight': 0.40,
                    })
        data['infra_projects'] = projects
        result = PortalResult(self.portal_name, 'OK' if projects or data['table_records'] else 'EMPTY_PAGE', self.url, query, data)
        self._save(output_dir, result)
        return result
