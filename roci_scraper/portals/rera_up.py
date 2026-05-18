from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import PortalAdapter, PortalResult
from ..utils import haversine_km

class ReraUpAdapter(PortalAdapter):
    portal_name = 'rera_up'
    url = 'https://rera.up.gov.in'

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

        data = self._generic_parse(snap.html, snap.text, ['registered project', 'project', 'registration', 'status', 'promoter', 'units'])
        projects = []
        for row in data.get('table_records', [])[:50]:
            joined = ' '.join(str(v) for v in row.values())
            if not joined.strip():
                continue
            name = str(row.get('Project Name') or row.get('Name') or row.get('Project') or joined[:180])
            reg = str(row.get('Registration No') or row.get('Registration Number') or row.get('Reg No') or row.get('Reg Number') or '')
            status = str(row.get('Status') or row.get('Project Status') or row.get('Stage') or '')
            units_raw = row.get('Units') or row.get('No. of Units') or row.get('Number of Units') or row.get('Apartments') or 0
            try:
                units = int(float(str(units_raw).replace(',', '').strip() or 0))
            except Exception:
                units = 0
            if units < 50:
                scale = 0.60
            elif units <= 200:
                scale = 0.80
            else:
                scale = 1.00
            s = status.lower()
            if any(k in s for k in ['revoked', 'lapsed', 'cancelled', 'withdrawn']):
                stage = -0.30
            elif any(k in s for k in ['completed', 'completion', 'oc']):
                stage = 0.60
            elif any(k in s for k in ['under construction', 'construction', 'progress']):
                stage = 1.00
            elif any(k in s for k in ['launched', 'development']):
                stage = 0.70
            else:
                stage = 0.50
            projects.append({
                'name': name,
                'reg_number': reg,
                'scale_weight': scale,
                'stage_multiplier': stage,
                'distance_km': 999.0,
            })
        if not projects and snap.text:
            lines = [l.strip() for l in snap.text.splitlines() if l.strip()]
            for line in lines[:40]:
                if any(k in line.lower() for k in ['project', 'registered']):
                    projects.append({
                        'name': line[:220],
                        'reg_number': '',
                        'scale_weight': 0.60,
                        'stage_multiplier': 0.50,
                        'distance_km': 999.0,
                    })
        data['rera_projects'] = projects
        result = PortalResult(self.portal_name, 'OK' if projects or data['table_records'] else 'EMPTY_PAGE', self.url, query, data)
        self._save(output_dir, result)
        return result
