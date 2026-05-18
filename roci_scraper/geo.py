from __future__ import annotations

import re
from typing import Optional

from .utils import haversine_km, normalize_whitespace

def classify_tender_type(title: str) -> str:
    t = normalize_whitespace(title).lower()
    mapping = [
        ('highway', ['highway', 'nh', 'nhai', 'national highway']),
        ('airport', ['airport', 'aai', 'airstrip']),
        ('metro', ['metro', 'mrt', 'rapid transit', 'mrts']),
        ('expressway', ['expressway', 'toll road']),
        ('railway', ['railway', 'rail', 'station', 'rites']),
        ('industrial', ['industrial corridor', 'dmic', 'akic', 'manufacturing']),
        ('smart', ['smart city', 'integrated township']),
        ('state_highway', ['state highway', 'sh', 'mdr']),
        ('utility', ['power', 'electricity', 'substation', 'grid', 'utility', 'water', 'sewerage', 'drainage', 'pipeline']),
    ]
    for label, kws in mapping:
        if any(k in t for k in kws):
            return label
    return 'unknown'

def extract_place_hint(title: str) -> str:
    title = re.sub(r'\([^)]*\)', ' ', title or '')
    m = re.search(r'(?:near|at|for|to|around)\s+([A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f\- ]{2,60})', title, re.I)
    if m:
        return normalize_whitespace(m.group(1))
    return normalize_whitespace(title[:80])

def parse_stage(text: str) -> float:
    t = (text or '').lower()
    rules = {
        'cancelled': 0.0, 'withdrawn': 0.0, 'scrapped': 0.0,
        'work order': 1.0, 'agreement signed': 1.0,
        'under execution': 0.90, 'under construction': 0.90,
        'loa': 0.70, 'award': 0.70,
        'pre-bid': 0.55, 'technical evaluation': 0.55,
        'published': 0.40, 'open': 0.40, 'tender floated': 0.40,
        'completed': 0.30, 'handed over': 0.30, 'closure': 0.30,
    }
    for key, val in rules.items():
        if key in t:
            return val
    return 0.40

def infer_project_distance(subject_lat: float, subject_lng: float, proj_lat: float | None, proj_lng: float | None) -> float:
    if proj_lat is None or proj_lng is None:
        return 999.0
    return haversine_km(subject_lat, subject_lng, proj_lat, proj_lng)
