from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from .normalize import normalize_portal_payloads
from .schema import ScoreInput
from .scorer import compute_roci
from .utils import load_json, save_json, safe_float
from .validator import cross_validate
from .zone_detector import detect_zone
from .portals.registry import ALL_PORTALS

def load_master_plan(ref_dir: Path, district: str) -> Dict[str, Any]:
    mp = load_json(ref_dir / 'master_plan.json')
    return mp.get(district, mp['__default'])

def build_base(lat: float, lng: float, area_sqft: float, gatta_number: str | None, zone_type: str, ref_dir: Path) -> Dict[str, Any]:
    zone = detect_zone(lat, lng, ref_dir)
    master = load_master_plan(ref_dir, zone.district)
    return {
        'lat': lat,
        'lng': lng,
        'area_sqft': area_sqft,
        'gatta_number': gatta_number,
        'zone_type': zone_type or 'urban_expansion',
        'lambda_decay': zone.lambda_decay,
        'clu_permitted': master['clu_permitted'],
        'far_subject': master['far_subject'],
        'far_benchmark': master['far_benchmark'],
        'district': zone.district,
        'sro_id': zone.sro_id,
    }

def merge_fixture(raw: Dict[str, Any], fixture: Path | None) -> Dict[str, Any]:
    if not fixture:
        return raw
    if not fixture.exists():
        raise FileNotFoundError(f'Fixture not found: {fixture}')
    extra = json.loads(fixture.read_text(encoding='utf-8'))
    # Only fill missing fields from a fixture; do not override live portal data.
    merged = dict(raw)
    for k, v in extra.items():
        if k not in merged or merged[k] in (None, '', [], {}):
            merged[k] = v
    return merged

def run_pipeline(lat: float, lng: float, area_sqft: float, gatta_number: str | None, zone_type: str, output_dir: Path, headless: bool = True, fixture: Path | None = None, fixture_only: bool = False) -> Dict[str, Any]:
    ref_dir = Path(__file__).resolve().parent / 'ref_data'
    output_dir.mkdir(parents=True, exist_ok=True)
    portal_out = output_dir / 'portal_outputs'
    portal_out.mkdir(parents=True, exist_ok=True)

    base = build_base(lat, lng, area_sqft, gatta_number, zone_type, ref_dir)

    raw = {
        'clu_current': 2,
        'mutation_status': 'CLEAR',
        'n_current': 0,
        'n_previous': 0,
        'mu_district': 0.0,
        'sigma_district': 1.0,
        'p_current': 0.0,
        'p_previous': 0.0,
        'infra_projects': [],
        'rera_projects': [],
        'portals_scraped': 0,
        'portals_required': len(ALL_PORTALS),
        'hours_since_scrape': 0.0,
        'conflicts': 0,
        'validation_pairs': 2,
        'clu_risk_flag': 0,
        'clu_pending_flag': 0,
        'zoning_flag': 0,
        'bhoomi_prakar': '',
    }

    portals_ok = []
    portals_failed = []
    resolved_gatta = gatta_number  # may be filled in from bhunaksha during the run

    if fixture_only and fixture:
        # Skip all live scraping — use fixture as the sole data source.
        extra = json.loads(fixture.read_text(encoding='utf-8'))
        raw.update({k: v for k, v in extra.items() if not k.startswith('_')})
    else:
        for adapter in ALL_PORTALS:
            # If bhulekh has no gatta_number yet, try to get it from bhunaksha result
            if adapter.portal_name == 'bhulekh' and not resolved_gatta:
                resolved_gatta = raw.get('khasra_number') or None
                if resolved_gatta:
                    logger.info(f'[pipeline] Using khasra_number={resolved_gatta!r} from bhunaksha for bhulekh lookup')

            scrape_gatta = resolved_gatta if adapter.portal_name == 'bhulekh' else gatta_number
            result = adapter.scrape(lat=lat, lng=lng, district=base['district'], gatta_number=scrape_gatta, output_dir=portal_out, headless=headless)
            if result.status == 'OK':
                portals_ok.append(result.portal)
                raw.update(result.data)
                raw['portals_scraped'] += 1
            else:
                portals_failed.append(result.portal)

        raw = merge_fixture(raw, fixture)
    normalized = normalize_portal_payloads(raw, ref_dir)
    conflicts, pairs = cross_validate(normalized)
    normalized['conflicts'] = conflicts
    normalized['validation_pairs'] = max(pairs, 2)
    normalized.update(base)
    normalized['scrape_metadata'] = {
        'scraped_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'portals_ok': portals_ok,
        'portals_failed': portals_failed,
        'gatta_number': resolved_gatta,
        'lat': lat,
        'lng': lng,
        'area_sqft': area_sqft,
    }

    score_input = ScoreInput(**normalized)
    result = compute_roci(score_input.model_dump(exclude={'scrape_metadata'}))
    result['scrape_metadata'] = score_input.scrape_metadata.model_dump() if score_input.scrape_metadata else None
    save_json(output_dir / 'final_score.json', result)
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description='ROCI score engine')
    parser.add_argument('--lat', type=float, required=True)
    parser.add_argument('--lng', type=float, required=True)
    parser.add_argument('--area-sqft', type=float, required=True)
    parser.add_argument('--gatta-number', type=str, default=None)
    parser.add_argument('--zone-type', type=str, default='urban_expansion')
    parser.add_argument('--output-dir', type=Path, default=Path('out'))
    parser.add_argument('--fixture', type=Path, default=None, help='Optional local JSON fixture')
    parser.add_argument('--fixture-only', action='store_true', default=False, help='Skip live scraping; use fixture as sole data source')
    parser.add_argument('--headless', action='store_true', default=False)
    args = parser.parse_args()

    result = run_pipeline(
        lat=args.lat,
        lng=args.lng,
        area_sqft=args.area_sqft,
        gatta_number=args.gatta_number,
        zone_type=args.zone_type,
        output_dir=args.output_dir,
        headless=args.headless,
        fixture=args.fixture,
        fixture_only=args.fixture_only,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
