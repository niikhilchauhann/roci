"""Assemble a consolidated, human-readable report for the latest pipeline run.

The streaming pipeline persists a score file plus one JSON per portal. The SSE
result only carries the score, so this reads the saved files and pulls out the
important fields for a document-style screen.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure roci_scraper is importable (repo root) for the circle-rate lookup.
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from roci_scraper.circle_rate import lookup_circle_rate
except Exception:  # pragma: no cover - keep report working if data missing
    lookup_circle_rate = None  # type: ignore

try:
    from roci_scraper.portals.bhulekh import _parse_owners_from_page
except Exception:  # pragma: no cover
    _parse_owners_from_page = None  # type: ignore

try:
    from roci_scraper.portals.rera_up import project_coords as _rera_coords
    from roci_scraper.utils import haversine_km as _haversine_km
except Exception:  # pragma: no cover
    _rera_coords = None  # type: ignore
    _haversine_km = None  # type: ignore


def _load(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _portal_data(portal_out: Path, name: str) -> Dict[str, Any]:
    blob = _load(portal_out / f"{name}.json")
    return blob.get("data", {}) if isinstance(blob, dict) else {}


def _to_dms(lat: float, lng: float) -> str:
    def part(v: float, pos: str, neg: str) -> str:
        hemi = pos if v >= 0 else neg
        a = abs(v)
        d = int(a)
        m = int((a - d) * 60)
        s = ((a - d) * 60 - m) * 60
        return f"{d}°{m}'{s:.1f}\"{hemi}"
    return f"{part(lat, 'N', 'S')} {part(lng, 'E', 'W')}"


def _parse_owners(raw: Any) -> List[Dict[str, str]]:
    """bhulekh owner_names may be stringified dicts; normalise to clean objects."""
    owners: List[Dict[str, str]] = []
    if not isinstance(raw, list):
        return owners
    for item in raw:
        if isinstance(item, dict):
            d = item
        elif isinstance(item, str):
            try:
                parsed = ast.literal_eval(item)
                d = parsed if isinstance(parsed, dict) else {"name": item}
            except Exception:
                d = {"name": item}
        else:
            continue
        name = str(d.get("name", "")).strip()
        if not name:
            continue
        owners.append({
            "name": name,
            "father": str(d.get("father", "")).strip(),
            "address": str(d.get("address", "")).strip(),
        })
    return owners


# Bhumidhar class suffix (Devanagari → English letter): 1-क = 1-A, 1-ख = 1-B, …
_BHU_LETTER = {'क': 'A', 'ख': 'B', 'ग': 'C', 'घ': 'D', 'ङ': 'E'}


def _bhoomi_code_en(code: str) -> str:
    return ''.join(_BHU_LETTER.get(ch, ch) for ch in (code or ''))


def _fasli_year(khatauni_text: str) -> str:
    """Pull the Fasli (khatauni) year line, e.g. '1428-1433 (01 Jul, 2020 ...)'."""
    if not khatauni_text:
        return ""
    # Page text may stay in Hindi when the English language switch fails, so
    # match both "Fasli Year" and "फसली वर्ष".
    m = re.search(r'(?:Fasli\s*Year|फसली\s*वर्ष)\s*[:\-]?\s*([^\n]+)', khatauni_text, re.I)
    return m.group(1).strip() if m else ""


def build_run_report(run_dir: Path) -> Dict[str, Any]:
    """Read a completed run directory and return the consolidated report."""
    score = _load(run_dir / "final_score.json")
    if not score:
        return {"status": "NO_RUN", "message": "No completed pipeline run found yet."}

    meta = score.get("scrape_metadata") or {}
    echo = score.get("inputs_echo") or {}
    components = score.get("components") or {}

    portal_out = run_dir / "portal_outputs"
    igrsup = _portal_data(portal_out, "igrsup")
    bhulekh = _portal_data(portal_out, "bhulekh")
    cppp = _portal_data(portal_out, "cppp_gem")
    rera = _portal_data(portal_out, "rera_up")
    # bhunaksha.json may be a leftover from a previous run (it's skipped when a
    # gatta number is supplied). Only trust it if bhunaksha actually ran this
    # round; otherwise rely on the user-selected village in metadata.
    bhunaksha = (
        _portal_data(portal_out, "bhunaksha")
        if "bhunaksha" in (meta.get("portals_ok") or [])
        else {}
    )

    lat = meta.get("lat")
    lng = meta.get("lng")
    district = echo.get("district") or igrsup.get("district") or "Ayodhya"

    # Infra (CPPP/GeM): keep the most relevant — infra-org first, then nearest.
    infra_all: List[Dict[str, Any]] = cppp.get("infra_projects") or []
    infra_sorted = sorted(
        infra_all,
        key=lambda p: (not p.get("is_infra_org", False), p.get("distance_km", 9e9)),
    )
    infra_projects = [
        {
            "title": p.get("title", ""),
            "org": p.get("org", ""),
            "type": p.get("type", ""),
            "stage": p.get("stage", ""),
            "distance_km": p.get("distance_km"),
            "closing_date": p.get("closing_date", ""),
            "is_infra_org": bool(p.get("is_infra_org", False)),
        }
        for p in infra_sorted[:8]
    ]

    # RERA: override distance with authoritative up-rera coordinates when we
    # have them (exact), so already-saved runs don't show stale geocoded values.
    rera_all: List[Dict[str, Any]] = rera.get("rera_projects") or []
    if _rera_coords and _haversine_km and isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        for p in rera_all:
            c = _rera_coords(p.get("reg_number", ""))
            if c:
                d_km = round(_haversine_km(lat, lng, c[0], c[1]), 3)
                p["distance_km"] = d_km
                p["distance_accuracy"] = "exact"
                p["within_radius"] = d_km <= 10.0
    rera_sorted = sorted(rera_all, key=lambda p: p.get("distance_km", 9e9))
    rera_projects = [
        {
            "name": p.get("name", ""),
            "promoter": p.get("promoter", ""),
            "type": p.get("project_type", ""),
            "distance_km": p.get("distance_km"),
            "distance_accuracy": p.get("distance_accuracy", "village"),
            "within_radius": p.get("within_radius", True),
            "status": p.get("status_text", ""),
            "completion": p.get("proposed_completion", ""),
            "village": p.get("village", "") or (p.get("detail") or {}).get("Village/Locality/Sector", ""),
            "gata_numbers": p.get("gata_numbers", []),
            "reg_number": p.get("reg_number", ""),
        }
        for p in rera_sorted
    ]

    area_sqft = meta.get("area_sqft")

    # Base circle rate (INR/sq m) for the parcel's revenue village. The
    # user-selected village (in meta) is authoritative; bhunaksha's spatial
    # result is only a fallback when no village was selected.
    circle_rate: Dict[str, Any] | None = None
    giscode = meta.get("giscode") or bhunaksha.get("giscode") or ""
    tehsil_code = meta.get("tehsil_code") or (giscode[3:8] if len(giscode) >= 8 else None)
    if lookup_circle_rate and tehsil_code:
        cr = lookup_circle_rate(
            tehsil_code=tehsil_code,
            village_hi=meta.get("village_hi") or bhunaksha.get("village_name_hi"),
            village_en=meta.get("village") or bhunaksha.get("village_name"),
        )
        if cr:
            rate = cr.get("base_rate_per_sqm")
            if isinstance(rate, (int, float)) and isinstance(area_sqft, (int, float)):
                cr["estimated_value_inr"] = round(rate * (area_sqft / 10.7639))
            circle_rate = cr

    return {
        "status": "OK",
        "summary": {
            "roci_final": score.get("roci_final"),
            "zone_label": score.get("zone_label"),
            "c_score": components.get("c_score"),
            "risk_flags": score.get("risk_flags") or [],
            "scraped_at": meta.get("scraped_at"),
            "portals_ok": meta.get("portals_ok") or [],
            "portals_failed": meta.get("portals_failed") or [],
        },
        "location": {
            "lat": lat,
            "lng": lng,
            "dms": _to_dms(lat, lng) if isinstance(lat, (int, float)) and isinstance(lng, (int, float)) else None,
            "district": district,
            # Prefer the village the user selected; bhunaksha's village is a
            # spatial hit for the clicked point and may differ from the search.
            "village": meta.get("village") or bhunaksha.get("village_name"),
            "village_code": meta.get("village_code") or bhunaksha.get("village_code"),
            "giscode": meta.get("giscode") or bhunaksha.get("giscode"),
            # Prefer the gata the user actually searched (confirmed by bhulekh).
            # bhunaksha.khasra_number is a *spatial* hit for the clicked point and
            # may be a different plot, so only use it as a last resort.
            "khasra": bhulekh.get("khasra_no") or meta.get("gatta_number") or bhunaksha.get("khasra_number"),
            "khata_number": bhulekh.get("khata_number"),
            "gatta_number": meta.get("gatta_number"),
            "area_ha": bhulekh.get("area_ha"),
            "area_sqft": round(area_sqft, 1) if isinstance(area_sqft, (int, float)) else area_sqft,
        },
        "registry": {
            "sro_code": igrsup.get("sro_code"),
            "sro_name": igrsup.get("sro_name"),
            "n_current": igrsup.get("n_current"),
            "n_previous": igrsup.get("n_previous"),
        },
        "circle_rate": circle_rate,
        "land_record": {
            "bhoomi_prakar": bhulekh.get("bhoomi_prakar"),
            "bhoomi_prakar_en": _bhoomi_code_en(bhulekh.get("bhoomi_prakar", "")),
            "bhoomi_prakar_desc": bhulekh.get("bhoomi_prakar_desc"),
            "mutation_status": bhulekh.get("mutation_status"),
            "clu_current": bhulekh.get("clu_current"),
            "fasli_year": bhulekh.get("fasli_year") or _fasli_year(bhulekh.get("khatauni_text", "")),
            "owners": _parse_owners(bhulekh.get("owner_names"))
            or (_parse_owners_from_page(bhulekh.get("khatauni_text", "")) if _parse_owners_from_page else []),
            "all_khasras": bhulekh.get("all_khasras") or [],
        },
        "plot_info_raw": (bhunaksha.get("plot_info") or {}).get("raw", "") if isinstance(bhunaksha.get("plot_info"), dict) else "",
        "infra_projects": infra_projects,
        "rera_projects": rera_projects,
    }
