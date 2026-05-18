from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .utils import load_json

@dataclass
class ZoneResult:
    district: str
    sro_id: str
    lambda_decay: float

def detect_zone(lat: float, lng: float, ref_dir: Path) -> ZoneResult:
    data = load_json(ref_dir / 'sro_boundaries.json')
    # Demo fallback only. For production, replace with polygon lookup against PostGIS.
    return ZoneResult(
        district=data.get('__default', {}).get('district', 'Ayodhya'),
        sro_id=data.get('__default', {}).get('sro_id', 'AYD-01'),
        lambda_decay=float(data.get('__default', {}).get('lambda_decay', 0.15)),
    )
