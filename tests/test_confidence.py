from roci_scraper.scorer import compute_roci


def test_suppressed_when_confidence_low():
    d = {
        "zone_type": "agricultural_greenfield",
        "clu_current": 2, "clu_permitted": 6,
        "months_since_clu_change": 0, "lambda_decay": 0.15,
        "n_current": 5, "mu_district": 8.0, "sigma_district": 3.0,
        "infra_projects": [], "rera_projects": [],
        "far_subject": 1.2, "far_benchmark": 1.3,
        "mutation_status": "CLEAR",
        "portals_scraped": 2,
        "portals_required": 5,
        "hours_since_scrape": 0.5,
        "conflicts": 1, "validation_pairs": 2,
    }
    res = compute_roci(d)
    assert res["status"] == "SUPPRESSED"
