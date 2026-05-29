from roci_scraper.scorer import compute_roci


def test_testcase_b_disputed_title_risk_cap():
    """Case B: strong base score but DISPUTED title + CLU risk flag triggers -20 cap."""
    d = {
        "zone_type": "urban_expansion",
        "clu_current": 3, "clu_permitted": 7,
        "months_since_clu_change": 6, "lambda_decay": 0.15,
        "n_current": 55, "n_previous": 30,
        "mu_district": 31.0, "sigma_district": 10.3,
        "p_current": 0, "p_previous": 0,
        "infra_projects": [
            {"type_weight": 1.0, "distance_km": 0.5, "stage_multiplier": 1.0},
        ],
        "rera_projects": [
            {"scale_weight": 0.8, "distance_km": 1.0, "stage_multiplier": 1.0},
        ],
        "far_subject": 2.0, "far_benchmark": 1.5,
        "mutation_status": "DISPUTED",   # -12
        "clu_risk_flag": -10,             # -10  → total -22 → capped at -20
        "portals_scraped": 5, "portals_required": 5,
        "hours_since_scrape": 1.0, "conflicts": 1, "validation_pairs": 2,
    }
    res = compute_roci(d)
    assert res["status"] == "OK"
    assert 30 <= res["roci_final"] <= 55, f"Expected 30–55, got {res['roci_final']}"
    assert res["components"]["r_total"] == -20, "Risk cap at -20 should trigger"


def test_testcase_a_matches_formula_as_written():
    d = {
        "zone_type": "urban_expansion",
        "clu_current": 3, "clu_permitted": 7,
        "months_since_clu_change": 14, "lambda_decay": 0.15,
        "n_current": 47, "n_previous": 28,
        "mu_district": 31.0, "sigma_district": 10.3,
        "p_current": 0, "p_previous": 0,
        "infra_projects": [
            {"type_weight": 0.75, "distance_km": 0.4, "stage_multiplier": 1.0},
            {"type_weight": 0.60, "distance_km": 0.9, "stage_multiplier": 0.7},
            {"type_weight": 0.50, "distance_km": 1.4, "stage_multiplier": 0.4},
        ],
        "rera_projects": [],
        "far_subject": 2.0, "far_benchmark": 1.76,
        "mutation_status": "PENDING",
        "portals_scraped": 5, "portals_required": 5,
        "hours_since_scrape": 2.5, "conflicts": 0, "validation_pairs": 2,
    }
    res = compute_roci(d)
    assert res["status"] == "OK"
    assert abs(res["roci_final"] - 50.93) <= 0.5
    assert res["zone_label"] == "Zone 3 — Watch"
    assert abs(res["components"]["clu_t"] - 0.4197) <= 0.0005
    assert abs(res["components"]["rv_t"] - 0.8254) <= 0.0005
