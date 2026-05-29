"""
cache_igrsup_sros.py

Runs the IGRSUP deed search for all 5 Ayodhya SROs and saves the results to
out/igrsup_sro_cache.json. Appends to any existing cache — safe to re-run for
a subset after a partial failure.

Usage:
    python scripts/cache_igrsup_sros.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roci_scraper.portals.igrsup import (
    _DISTRICT_CODE,
    _fetch_all_villages,
    _filter_90_days,
    _load_cookies,
    _load_villages,
    _lookup_circle_rate,
    _median_price_per_sqft,
)

# ---------------------------------------------------------------------------

_ALL_SROS: dict[str, str] = {
    "074": "Rudauli",
    "120": "Sadar",
    "121": "Bikapur",
    "122": "Milkipur",
    "123": "Sohawal",
}

# Subset to run — set to None to run all SROs
_SRO_NAMES_TO_RUN: dict[str, str] | None = {
    "122": "Milkipur",
    "123": "Sohawal",
}

_OUTPUT_FILE = Path(__file__).resolve().parent.parent / "out" / "igrsup_sro_cache.json"
_MAX_DETAIL_FETCHES = 10
_DISTRICT = "Ayodhya"

# ---------------------------------------------------------------------------


def process_sro(cookies, villages, sro_code: str, sro_name: str, now: datetime) -> dict:
    current_start = now - timedelta(days=90)
    prev_start    = now - timedelta(days=180)
    prev_end      = current_start

    print(f"  [{sro_code}] {sro_name}: fetching villages...", flush=True)
    all_rows = _fetch_all_villages(cookies, villages, sro_code)
    print(f"  [{sro_code}] {sro_name}: got {len(all_rows)} unique deed rows", flush=True)

    current_rows  = _filter_90_days(all_rows, current_start, now)
    previous_rows = _filter_90_days(all_rows, prev_start, prev_end)

    n_current  = len(current_rows)
    n_previous = len(previous_rows)

    print(f"  [{sro_code}] {sro_name}: n_current={n_current}, n_previous={n_previous} — fetching detail pages...", flush=True)
    p_current_median  = _median_price_per_sqft(cookies, current_rows,  _MAX_DETAIL_FETCHES)
    p_previous_median = _median_price_per_sqft(cookies, previous_rows, _MAX_DETAIL_FETCHES)

    deed_ref = None
    if current_rows:
        sorted_rows = sorted(
            (r for r in current_rows if r.get("_reg_date")),
            key=lambda r: r["_reg_date"],
            reverse=True,
        )
        if sorted_rows:
            deed_ref = sorted_rows[0].get("registration_no")

    circle_rate = _lookup_circle_rate(_DISTRICT, sro_name)
    print(f"  [{sro_code}] {sro_name}: done — p_current_median={p_current_median}", flush=True)

    return {
        "sro_code":                  sro_code,
        "sro_name":                  sro_name,
        "n_current":                 n_current,
        "n_previous":                n_previous,
        "p_current_median":          p_current_median,
        "p_previous_median":         p_previous_median,
        "deed_ref":                  deed_ref,
        "circle_rate_crore_per_acre": circle_rate,
        "current_window_start":      current_start.strftime("%Y-%m-%d"),
        "current_window_end":        now.strftime("%Y-%m-%d"),
        "previous_window_start":     prev_start.strftime("%Y-%m-%d"),
        "previous_window_end":       prev_end.strftime("%Y-%m-%d"),
        "total_deed_rows":           len(all_rows),
        "fetched_at":                now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main():
    # Load existing cache so we don't lose already-fetched SROs
    existing: dict = {}
    if _OUTPUT_FILE.exists():
        try:
            cached = json.loads(_OUTPUT_FILE.read_text(encoding="utf-8"))
            existing = cached.get("sros", {})
            print(f"Loaded existing cache with {len(existing)} SRO(s): {list(existing.keys())}", flush=True)
        except Exception as exc:
            print(f"Warning: could not load existing cache — {exc}", flush=True)

    print("Loading session and villages...", flush=True)
    cookies  = _load_cookies()
    villages = _load_villages()
    if not villages:
        print("ERROR: villages.json not found. Run generate-villages.js first.")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    sros_to_run = _SRO_NAMES_TO_RUN if _SRO_NAMES_TO_RUN is not None else _ALL_SROS

    for sro_code, sro_name in sros_to_run.items():
        try:
            result = process_sro(cookies, villages, sro_code, sro_name, now)
            existing[sro_code] = result
        except Exception as exc:
            print(f"  [{sro_code}] {sro_name}: ERROR — {exc}", flush=True)
            existing[sro_code] = {
                "sro_code":   sro_code,
                "sro_name":   sro_name,
                "error":      str(exc),
                "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        # Save after every SRO so progress is never lost
        _save(existing, now)

    _save(existing, now, final=True)


def _save(sros: dict, now: datetime, final: bool = False):
    n_values = [r["n_current"] for r in sros.values() if "n_current" in r]
    mu_district    = round(statistics.mean(n_values),  2) if len(n_values) >= 2 else None
    sigma_district = round(statistics.stdev(n_values), 2) if len(n_values) >= 2 else None

    all_done = set(sros.keys()) >= set(_ALL_SROS.keys())
    note = (
        "n_current/n_previous = deed counts in 90-day windows; p_*_median in INR/sqft"
        if all_done else
        f"Partial cache — completed SROs: {sorted(sros.keys())}"
    )

    output = {
        "__meta": {
            "district":       _DISTRICT,
            "district_code":  _DISTRICT_CODE,
            "generated_at":   now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mu_district":    mu_district,
            "sigma_district": sigma_district,
            "note":           note,
        },
        "sros": sros,
    }

    _OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    if final:
        print(f"\n{'='*55}")
        print(f"Saved → {_OUTPUT_FILE}")
        print(f"mu_district={mu_district}  sigma_district={sigma_district}")
        print("SRO summary:")
        for code in sorted(sros.keys()):
            r = sros[code]
            if "error" in r:
                print(f"  {code}  {r['sro_name']:12}  ERROR: {r['error']}")
            else:
                print(
                    f"  {code}  {r['sro_name']:12}  "
                    f"n_curr={r['n_current']:4}  n_prev={r['n_previous']:4}  "
                    f"p_med={r['p_current_median']}"
                )
        print("="*55)
    else:
        print(f"  [cache saved → {_OUTPUT_FILE.name}]", flush=True)


if __name__ == "__main__":
    main()
