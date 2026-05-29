from __future__ import annotations

import re
import time
from typing import Tuple

from .utils import haversine_km, normalize_whitespace

_NOMINATIM_LAST_CALL = 0.0  # module-level throttle (1 req/sec policy)

def geocode_nominatim(query: str, country_code: str = 'in') -> Tuple[float, float] | None:
    """Return (lat, lng) for a query string via Nominatim OSM. Rate-limited to 1 req/sec."""
    global _NOMINATIM_LAST_CALL
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    except ImportError:
        return None

    now = time.monotonic()
    gap = now - _NOMINATIM_LAST_CALL
    if gap < 1.0:
        time.sleep(1.0 - gap)

    geolocator = Nominatim(user_agent='roci-engine/0.1 (ayodhya-demo)')
    _NOMINATIM_LAST_CALL = time.monotonic()
    try:
        loc = geolocator.geocode(f'{query}, Uttar Pradesh, India', timeout=10, country_codes=country_code)
        if loc:
            return (loc.latitude, loc.longitude)
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return None

def classify_tender_type(title: str) -> str:
    """Section 4.2: keyword-based project type classification."""
    t = normalize_whitespace(title).lower()
    # Order matters — most specific first
    mapping = [
        ('highway',       ['national highway', 'nhai', 'nh-', ' nh ']),
        ('airport',       ['airport', 'aai', 'airstrip', 'aerodrome']),
        ('metro',         ['metro', 'rapid transit', 'mrts', 'mrt']),
        ('expressway',    ['expressway', 'toll road', 'toll plaza']),
        ('railway',       ['railway', 'rail line', 'rail corridor', 'station', 'rites', 'ircon']),
        ('industrial',    ['industrial corridor', 'dmic', 'akic', 'cbic', 'manufacturing zone']),
        ('smart',         ['smart city', 'integrated township', 'amrut']),
        ('state_highway', ['state highway', ' sh-', ' mdr ']),
        ('power_utility', ['power', 'electricity', 'substation', 'grid', 'transmission']),
        ('water_utility', ['water', 'sewerage', 'sewage', 'drainage', 'pipeline', 'irrigation']),
        ('commercial',    ['commercial complex', 'mall', 'market complex', 'trade centre']),
        ('highway',       ['highway']),  # generic highway after specific ones
        ('railway',       ['rail']),
        ('industrial',    ['industrial']),
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
    """Section 4.3: procurement stage → stage_multiplier."""
    t = (text or '').lower()
    rules = [
        # Zero-value stages checked first so a cancelled tender is never scored
        (['cancelled', 'withdrawn', 'scrapped'], 0.0),
        (['work order', 'agreement signed', 'wo issued', 'wo'], 1.0),
        (['under execution', 'under construction', 'uc'], 0.90),
        (['loa issued', 'letter of award', 'loa', 'award'], 0.70),
        (['pre-bid', 'pre bid', 'technical evaluation'], 0.55),
        (['published', 'open', 'tender floated', 'tf', 'active'], 0.40),
        (['completed', 'closure', 'handed over', 'completion certificate', 'oc obtained'], 0.30),
    ]
    for keywords, multiplier in rules:
        if any(k in t for k in keywords):
            return multiplier
    return 0.40

def infer_project_distance(subject_lat: float, subject_lng: float, proj_lat: float | None, proj_lng: float | None) -> float:
    if proj_lat is None or proj_lng is None:
        return 999.0
    return haversine_km(subject_lat, subject_lng, proj_lat, proj_lng)
