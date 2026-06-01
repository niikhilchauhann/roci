from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable

from rapidfuzz import fuzz, process

from .utils import load_json, normalize_whitespace, safe_float, safe_int

_HINDI_SPACES = re.compile(r'[\u200b\u200c\u200d\ufeff]')
_MULTISPACE = re.compile(r'\s+')

def normalize_text(text: str) -> str:
    text = unicodedata.normalize('NFKC', text or '')
    text = _HINDI_SPACES.sub('', text)
    text = text.replace('\xa0', ' ')
    text = text.replace('।', ' ')
    text = _MULTISPACE.sub(' ', text)
    return text.strip()

def _lookup_mapping(text: str, ref_dir: Path) -> int:
    mapping = load_json(ref_dir / 'clu_map.json')
    if not text:
        return 2
    candidates = list(mapping.keys())
    best = process.extractOne(
        normalize_text(text),
        candidates,
        scorer=fuzz.WRatio,
    )
    if not best:
        return 2
    name, score, _ = best
    if score < 64:
        return 2
    return int(mapping[name])

def normalize_portal_payloads(raw: Dict[str, Any], ref_dir: Path) -> Dict[str, Any]:
    out = dict(raw)

    # Core numeric fields
    for key, default in [
        ('n_current', 0), ('n_previous', 0), ('mu_district', 0.0), ('sigma_district', 1.0),
        ('p_current', 0.0), ('p_previous', 0.0), ('month_since_clu_change', 0),
        ('months_since_clu_change', 0), ('far_subject', 1.5), ('far_benchmark', 1.5),
        ('portals_scraped', 0), ('portals_required', 5), ('hours_since_scrape', 0.0),
        ('conflicts', 0), ('validation_pairs', 2), ('clu_risk_flag', 0), ('clu_pending_flag', 0), ('zoning_flag', 0),
    ]:
        if key in out:
            out[key] = safe_float(out[key], default) if isinstance(default, float) else safe_int(out[key], default)

    out['sigma_district'] = max(float(out.get('sigma_district', 1.0)), 1.0)

    # CLU mapping — bhoomi_prakar from Bhulekh always overrides the default
    if out.get('bhoomi_prakar'):
        out['clu_current'] = _lookup_mapping(str(out['bhoomi_prakar']), ref_dir)
    out['clu_current'] = safe_int(out.get('clu_current'), 2)
    out['clu_permitted'] = safe_int(out.get('clu_permitted'), 7)
    out['mutation_status'] = normalize_whitespace(str(out.get('mutation_status', 'CLEAR'))).upper() or 'CLEAR'
    if out['mutation_status'] not in {'CLEAR', 'PENDING', 'NOT_INIT', 'TAX_DUES', 'DISPUTED', 'UNKNOWN'}:
        out['mutation_status'] = 'UNKNOWN'

    # Normalize projects
    infra = []
    for p in out.get('infra_projects', []) or []:
        if isinstance(p, dict):
            p = dict(p)
            p['type_weight'] = safe_float(p.get('type_weight'), 0.4)
            p['distance_km'] = max(safe_float(p.get('distance_km'), 0.0), 0.0)
            p['stage_multiplier'] = safe_float(p.get('stage_multiplier'), 0.4)
            infra.append(p)
    out['infra_projects'] = infra

    rera = []
    for p in out.get('rera_projects', []) or []:
        if isinstance(p, dict):
            p = dict(p)
            p['scale_weight'] = safe_float(p.get('scale_weight'), 0.6)
            p['distance_km'] = max(safe_float(p.get('distance_km'), 0.0), 0.0)
            p['stage_multiplier'] = safe_float(p.get('stage_multiplier'), 0.5)
            rera.append(p)
    out['rera_projects'] = rera

    return out


def map_bhoomi_prakar(text: str, ref_dir: Path) -> int:
    """Backward-compatible helper used by the tests and older CLI fixtures."""
    return _lookup_mapping(text, ref_dir)

