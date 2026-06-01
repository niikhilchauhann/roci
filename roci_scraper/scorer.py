from __future__ import annotations

import math

ZONE_WEIGHTS = {
    'urban_expansion': (0.38, 0.32, 0.15, 0.15),
    'peri_urban': (0.35, 0.30, 0.20, 0.15),
    'agricultural_greenfield': (0.45, 0.15, 0.25, 0.15),
    'industrial_corridor': (0.25, 0.30, 0.30, 0.15),
    'rural_development': (0.30, 0.25, 0.30, 0.15),
    'smart_city': (0.30, 0.30, 0.25, 0.15),
}

MUTATION_PENALTIES = {
    'CLEAR': 0,
    'PENDING': -4,
    'NOT_INIT': -8,
    'TAX_DUES': -4,
    'DISPUTED': -12,
    'UNKNOWN': 0,
}

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))

def get_zone_label(score: float) -> str:
    if score >= 75:
        return 'Zone 5 — Strong Buy'
    if score >= 60:
        return 'Zone 4 — Buy with Verification'
    if score >= 45:
        return 'Zone 3 — Watch'
    if score >= 30:
        return 'Zone 2 — Hold'
    return 'Zone 1 — Avoid'

def compute_roci(d: dict) -> dict:
    clu_base = max(0.0, (d['clu_permitted'] - d['clu_current']) / 8.0)
    t_years = d.get('months_since_clu_change', 0) / 12.0
    clu_t = clu_base * math.exp(-d.get('lambda_decay', 0.15) * t_years)

    sigma = max(d.get('sigma_district', 1.0), 0.01)
    velocity_z = (d['n_current'] - d['mu_district']) / sigma

    price_vz = 0.0
    if d.get('p_previous', 0) > 0 and d.get('p_current', 0) > 0:
        price_vz = (d['p_current'] - d['p_previous']) / d['p_previous']

    rv_combined = 0.55 * velocity_z + 0.45 * price_vz if d.get('p_previous', 0) > 0 else velocity_z
    rv_t = sigmoid(rv_combined)

    R_MAX_INFRA = 5.0
    N_MAX_INFRA = 3.0
    is_raw = 0.0
    for p in d.get('infra_projects', []):
        is_raw += p['type_weight'] * math.exp(-p['distance_km'] / R_MAX_INFRA) * p['stage_multiplier']
    is_t = min(is_raw / N_MAX_INFRA, 1.0)

    R_MAX_RERA = 5.0
    N_MAX_RERA = 2.0
    rera_raw = 0.0
    for p in d.get('rera_projects', []):
        rera_raw += p['scale_weight'] * math.exp(-p['distance_km'] / R_MAX_RERA) * p['stage_multiplier']
    rera_d = min(max(rera_raw / N_MAX_RERA, -0.3), 1.0)

    zone = d.get('zone_type', 'urban_expansion')
    w1, w2, w3, w4 = ZONE_WEIGHTS.get(zone, ZONE_WEIGHTS['urban_expansion'])
    base_score = w1 * clu_t + w2 * rv_t + w3 * is_t + w4 * rera_d

    far_subject = d.get('far_subject', 1.5)
    far_benchmark = max(d.get('far_benchmark', 1.5), 0.1)
    far_h = min(far_subject / far_benchmark, 2.5)
    roci_pre = base_score * far_h * 100.0

    portals_scraped = d.get('portals_scraped', 5)
    portals_required = d.get('portals_required', 5)
    hours_since = d.get('hours_since_scrape', 0.0)
    conflicts = d.get('conflicts', 0)
    validation_pairs = d.get('validation_pairs', 2)

    d_completeness = portals_scraped / portals_required
    d_recency = math.exp(-hours_since / 72.0)
    d_consistency = 1.0 - (conflicts / max(validation_pairs, 1))
    c_score = (d_completeness * d_recency * d_consistency) ** (1.0 / 3.0)

    if c_score >= 0.80:
        c_adj = 1.0
    elif c_score >= 0.60:
        c_adj = c_score
    else:
        return {
            'status': 'SUPPRESSED',
            'reason': 'Data confidence below 0.60 — re-scrape required',
            'c_score': round(c_score, 3),
            'portals_scraped': portals_scraped,
        }

    roci_post_confidence = roci_pre * c_adj

    r_mutation = MUTATION_PENALTIES.get(d.get('mutation_status', 'CLEAR'), 0)
    r_clu_risk = d.get('clu_risk_flag', 0)
    r_clu_pending = d.get('clu_pending_flag', 0)
    r_zoning = d.get('zoning_flag', 0)
    r_total = max(-20, r_mutation + r_clu_risk + r_clu_pending + r_zoning)

    roci_final = max(0.0, roci_post_confidence + r_total)

    risk_flags = []
    if d.get('mutation_status') == 'TAX_DUES':
        risk_flags.append('Land tax dues outstanding')
    if d.get('mutation_status') == 'PENDING':
        risk_flags.append('Mutation pending')
    if d.get('mutation_status') == 'DISPUTED':
        risk_flags.append('Title disputed')

    return {
        'status': 'OK',
        'roci_final': round(roci_final, 2),
        'zone_label': get_zone_label(roci_final),
        'risk_flags': risk_flags,
        'components': {
            'clu_t': round(clu_t, 4),
            'rv_t': round(rv_t, 4),
            'is_t': round(is_t, 4),
            'rera_d': round(rera_d, 4),
            'base_score': round(base_score, 4),
            'far_h': round(far_h, 3),
            'roci_pre': round(roci_pre, 2),
            'c_score': round(c_score, 3),
            'c_adj': round(c_adj, 3),
            'roci_post_conf': round(roci_post_confidence, 2),
            'r_mutation': r_mutation,
            'r_clu_risk': r_clu_risk,
            'r_clu_pending': r_clu_pending,
            'r_zoning': r_zoning,
            'r_total': r_total,
            'velocity_z': round(velocity_z, 3),
            'clu_base': round(clu_base, 4),
        },
        'inputs_echo': {
            'zone_type': zone,
            'weights': (w1, w2, w3, w4),
            'mutation_status': d.get('mutation_status'),
            'clu_current': d.get('clu_current'),
            'clu_permitted': d.get('clu_permitted'),
        },
        'rera_projects': [
            {
                'name': p.get('name', ''),
                'reg_number': p.get('reg_number', ''),
                'distance_km': p.get('distance_km'),
                'scale_weight': p.get('scale_weight'),
                'stage_multiplier': p.get('stage_multiplier'),
                'status_text': p.get('status_text', ''),
                'promoter': p.get('promoter', ''),
            }
            for p in d.get('rera_projects', [])
        ],
    }
