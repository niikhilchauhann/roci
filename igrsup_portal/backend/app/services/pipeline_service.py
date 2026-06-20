from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import AsyncGenerator, Any, Dict

# Ensure roci_scraper package is importable from this backend
_ROOT = Path(__file__).resolve().parents[4]  # .../roci
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from roci_scraper.normalize import normalize_portal_payloads
from roci_scraper.schema import ScoreInput
from roci_scraper.scorer import compute_roci
from roci_scraper.utils import save_json
from roci_scraper.validator import cross_validate
from roci_scraper.portals.registry import ALL_PORTALS
from roci_scraper.main import build_base, merge_fixture

from datetime import datetime, timezone


def _event(kind: str, **kw) -> str:
    payload = json.dumps({"event": kind, **kw}, ensure_ascii=False)
    return f"data: {payload}\n\n"


async def stream_pipeline(
    lat: float,
    lng: float,
    area_sqft: float,
    gatta_number: str | None,
    zone_type: str,
    output_dir: Path,
    headless: bool = True,
    fixture_path: Path | None = None,
    fixture_only: bool = False,
    village: Dict[str, Any] | None = None,
) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    import os, importlib
    _pkg = importlib.util.find_spec("roci_scraper")
    if _pkg and _pkg.submodule_search_locations:
        ref_dir = Path(list(_pkg.submodule_search_locations)[0]) / "ref_data"
    else:
        ref_dir = Path(os.environ.get("ROCI_REF_DIR", str(Path(__file__).resolve().parents[4] / "roci_scraper" / "ref_data")))
    output_dir.mkdir(parents=True, exist_ok=True)
    portal_out = output_dir / "portal_outputs"
    portal_out.mkdir(parents=True, exist_ok=True)

    yield _event("start", total_portals=len(ALL_PORTALS), message="Pipeline initialised")

    # Stage 0 — zone detection
    yield _event("stage", stage=0, name="Zone Detection", message="Detecting zone and loading master plan...")
    try:
        base = await loop.run_in_executor(
            None, lambda: build_base(lat, lng, area_sqft, gatta_number, zone_type, ref_dir)
        )
    except Exception as exc:
        yield _event("error", stage=0, detail=str(exc))
        return
    yield _event("stage_done", stage=0, name="Zone Detection", district=base["district"], zone_type=base["zone_type"])

    raw: Dict[str, Any] = {
        "clu_current": 2,
        "mutation_status": "CLEAR",
        "n_current": 0,
        "n_previous": 0,
        "mu_district": 0.0,
        "sigma_district": 1.0,
        "p_current": 0.0,
        "p_previous": 0.0,
        "infra_projects": [],
        "rera_projects": [],
        "portals_scraped": 0,
        "portals_required": len(ALL_PORTALS),
        "hours_since_scrape": 0.0,
        "conflicts": 0,
        "validation_pairs": 2,
        "clu_risk_flag": 0,
        "clu_pending_flag": 0,
        "zoning_flag": 0,
        "bhoomi_prakar": "",
    }

    portals_ok: list[str] = []
    portals_failed: list[str] = []
    resolved_gatta = gatta_number

    if fixture_only:
        yield _event("stage", stage=1, name="Fixture Load", message="Loading fixture data (live scraping skipped)...")
        if fixture_path and fixture_path.exists():
            import json as _json
            extra = _json.loads(fixture_path.read_text(encoding="utf-8"))
            raw.update({k: v for k, v in extra.items() if not k.startswith("_")})
        yield _event("stage_done", stage=1, name="Fixture Load", message="Fixture loaded — skipped portals 2–5")
        # Mark all portal stages as skipped so the UI fills them
        for idx in range(1, len(ALL_PORTALS)):
            yield _event("stage_done", stage=idx + 1, name=ALL_PORTALS[idx].portal_name.upper(),
                         portal=ALL_PORTALS[idx].portal_name, status="SKIPPED", elapsed_s=0.0)
    else:
        # Stages 1–5: one per portal
        for idx, adapter in enumerate(ALL_PORTALS):
            stage_num = idx + 1
            portal = adapter.portal_name

            # Skip Bhunaksha if gatta number was already provided
            if portal == "bhunaksha" and resolved_gatta:
                yield _event("stage", stage=stage_num, name="BHUNAKSHA", portal=portal, message="Skipped — gatta number already provided")
                yield _event("stage_done", stage=stage_num, name="BHUNAKSHA", portal=portal, status="SKIPPED", elapsed_s=0.0)
                continue

            # After Bhunaksha runs, pick up the gatta number it found
            if portal == "bhulekh" and not resolved_gatta:
                resolved_gatta = raw.get("khasra_number") or raw.get("gatta_number") or None

            scrape_gatta = resolved_gatta if portal == "bhulekh" else None
            yield _event(
                "stage",
                stage=stage_num,
                name=portal.upper(),
                portal=portal,
                message=f"Scraping {portal}...",
            )
            t0 = time.monotonic()
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda a=adapter, g=scrape_gatta: a.scrape(
                        lat=lat,
                        lng=lng,
                        district=base["district"],
                        gatta_number=g,
                        output_dir=portal_out,
                        headless=headless,
                        **({"village": village} if a.portal_name in ("bhunaksha", "bhulekh") else {}),
                    ),
                )
                elapsed = round(time.monotonic() - t0, 1)
                if result.status == "OK":
                    portals_ok.append(portal)
                    raw.update(result.data)
                    raw["portals_scraped"] += 1
                    yield _event(
                        "stage_done",
                        stage=stage_num,
                        name=portal.upper(),
                        portal=portal,
                        status="OK",
                        elapsed_s=elapsed,
                        fields=list(result.data.keys()),
                    )
                elif portal == "cppp_gem" and result.status == "EMPTY_PAGE":
                    # CAPTCHA failure — show as failed in UI but merge empty
                    # infra_projects so pipeline can still compute a score
                    portals_failed.append(portal)
                    raw.setdefault("infra_projects", [])
                    yield _event(
                        "stage_failed",
                        stage=stage_num,
                        name=portal.upper(),
                        portal=portal,
                        error="CAPTCHA failed — infra score will be 0",
                        elapsed_s=elapsed,
                    )
                else:
                    portals_failed.append(portal)
                    yield _event(
                        "stage_failed",
                        stage=stage_num,
                        name=portal.upper(),
                        portal=portal,
                        error=result.note or None,
                        elapsed_s=elapsed,
                    )
            except Exception as exc:
                elapsed = round(time.monotonic() - t0, 1)
                portals_failed.append(portal)
                yield _event(
                    "stage_failed",
                    stage=stage_num,
                    name=portal.upper(),
                    portal=portal,
                    error=str(exc),
                    elapsed_s=elapsed,
                )

        if fixture_path:
            raw = await loop.run_in_executor(None, lambda: merge_fixture(raw, fixture_path))

    # Stage 6 — normalise + cross-validate
    yield _event("stage", stage=6, name="Normalise & Validate", message="Normalising portal payloads and running cross-validation...")
    try:
        normalized = await loop.run_in_executor(
            None, lambda: normalize_portal_payloads(raw, ref_dir)
        )
        conflicts, pairs = cross_validate(normalized)
        normalized["conflicts"] = conflicts
        normalized["validation_pairs"] = max(pairs, 2)
        normalized.update(base)
        normalized["scrape_metadata"] = {
            "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "portals_ok": portals_ok,
            "portals_failed": portals_failed,
            "gatta_number": resolved_gatta,
            "village": (village or {}).get("name"),
            # Persist the rest of the selected village so the report/circle-rate
            # still work when bhunaksha is skipped (gatta provided) or fails.
            "village_hi": (village or {}).get("name_hi"),
            "village_code": (village or {}).get("village_code"),
            "giscode": (village or {}).get("giscode"),
            "tehsil_code": (village or {}).get("tehsil_code"),
            "lat": lat,
            "lng": lng,
            "area_sqft": area_sqft,
        }
    except Exception as exc:
        yield _event("error", stage=6, detail=str(exc))
        return
    yield _event(
        "stage_done",
        stage=6,
        name="Normalise & Validate",
        conflicts=conflicts,
        portals_ok=portals_ok,
        portals_failed=portals_failed,
    )

    # Stage 7 — ROCI scoring
    yield _event("stage", stage=7, name="ROCI Score", message="Computing ROCI score...")
    try:
        score_input = ScoreInput(**normalized)
        final = await loop.run_in_executor(
            None, lambda: compute_roci(score_input.model_dump(exclude={"scrape_metadata"}))
        )
        final["scrape_metadata"] = (
            score_input.scrape_metadata.model_dump() if score_input.scrape_metadata else None
        )
        await loop.run_in_executor(None, lambda: save_json(output_dir / "final_score.json", final))
    except Exception as exc:
        yield _event("error", stage=7, detail=str(exc))
        return

    yield _event("stage_done", stage=7, name="ROCI Score", roci_final=final.get("roci_final"), status=final.get("status"))

    # Stage 8 — Done
    yield _event("done", stage=8, result=final)
