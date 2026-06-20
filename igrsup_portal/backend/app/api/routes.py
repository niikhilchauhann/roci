from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.models.api import (
    AnalysisHistoryListResponse,
    AnalysisHistoryRecord,
    BhulekhRequest,
    BhulekhResponse,
    BhunakshaRequest,
    BhunakshaResponse,
    HealthResponse,
    ScoreRequest,
    ScoreResponse,
)
from app.services.land_service import LandIntelligenceService
from app.services.pipeline_service import stream_pipeline
from app.services.report_service import build_run_report

router = APIRouter()


def get_land_service() -> LandIntelligenceService:
    return LandIntelligenceService()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="OK", service="roci-ayodhya-engine")


@router.post("/bhunaksha", response_model=BhunakshaResponse)
async def bhunaksha_lookup(
    payload: BhunakshaRequest,
    service: LandIntelligenceService = Depends(get_land_service),
) -> BhunakshaResponse:
    return await service.fetch_bhunaksha(payload)


@router.post("/bhulekh", response_model=BhulekhResponse)
async def bhulekh_lookup(
    payload: BhulekhRequest,
    service: LandIntelligenceService = Depends(get_land_service),
) -> BhulekhResponse:
    return await service.fetch_bhulekh(payload)


@router.post("/score", response_model=ScoreResponse)
async def score_land(
    payload: ScoreRequest,
    service: LandIntelligenceService = Depends(get_land_service),
) -> ScoreResponse:
    return await service.score(payload)


@router.get("/history", response_model=AnalysisHistoryListResponse)
async def history_list(
    limit: int = Query(default=50, ge=1, le=200),
    service: LandIntelligenceService = Depends(get_land_service),
) -> AnalysisHistoryListResponse:
    return AnalysisHistoryListResponse(status="OK", records=service.load_history(limit=limit))


@router.get("/history/export")
async def history_export(
    service: LandIntelligenceService = Depends(get_land_service),
) -> FileResponse:
    export_path = service.export_history_path()
    return FileResponse(
        path=export_path,
        media_type="text/csv",
        filename="analysis_history.csv",
    )


@router.get("/pipeline/stream")
async def pipeline_stream(
    lat: float = Query(...),
    lng: float = Query(...),
    area_sqft: float = Query(...),
    gatta_number: str | None = Query(default=None),
    zone_type: str = Query(default="urban_expansion"),
    headless: bool = Query(default=True),
    fixture_only: bool = Query(default=False),
    village_name: str | None = Query(default=None),
    village_hi: str | None = Query(default=None),
    village_code: str | None = Query(default=None),
    giscode: str | None = Query(default=None),
    tehsil: str | None = Query(default=None),
) -> StreamingResponse:
    import os
    _out_base = os.environ.get("ROCI_OUT_DIR", str(Path(__file__).resolve().parents[2] / "data"))
    output_dir = Path(_out_base) / "pipeline_runs"

    # Build the revenue-village payload for bhunaksha/bhulekh. The selected
    # village is resolved against ref_data/ayodhya_bhunaksha_villages.json so the
    # giscode/village_code/tehsil_code are authoritative — we don't depend on the
    # client sending a correct giscode. These codes drive bhunaksha (Path 0),
    # bhulekh, and the circle-rate lookup.
    village: dict | None = None
    if giscode or village_name or village_code:
        resolved = None
        try:
            from roci_scraper.village_lookup import resolve_village
            resolved = resolve_village(
                name=village_name, name_hi=village_hi,
                giscode=giscode, village_code=village_code, tehsil=tehsil,
            )
        except Exception:
            resolved = None
        if resolved:
            village = resolved
        else:
            # Couldn't match the ref data — fall back to whatever was sent.
            gc = giscode or ""
            village = {
                "name": village_name,
                "name_hi": village_hi,
                "village_code": village_code,
                "giscode": gc,
                "tehsil_code": gc[3:8] if len(gc) >= 8 else "",
            }
    import logging
    logging.getLogger("uvicorn.error").info(
        "PIPELINE REQUEST: gatta=%r village_name=%r giscode=%r -> resolved village=%r",
        gatta_number, village_name, giscode, village,
    )

    return StreamingResponse(
        stream_pipeline(
            lat=lat,
            lng=lng,
            area_sqft=area_sqft,
            gatta_number=gatta_number,
            zone_type=zone_type,
            output_dir=output_dir,
            headless=headless,
            fixture_only=fixture_only,
            village=village,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/pipeline/report")
async def pipeline_report() -> dict:
    """Consolidated document for the most recent pipeline run."""
    import os
    _out_base = os.environ.get("ROCI_OUT_DIR", str(Path(__file__).resolve().parents[2] / "data"))
    run_dir = Path(_out_base) / "pipeline_runs"
    return build_run_report(run_dir)


@router.get("/igrsup/cache")
async def igrsup_cache() -> dict:
    import json
    cache_path = Path(__file__).resolve().parents[4] / "out" / "igrsup_sro_cache.json"
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text(encoding="utf-8"))


@router.get("/portals/cppp")
async def cppp_last() -> dict:
    import json
    p = Path(__file__).resolve().parents[4] / "out" / "portal_outputs" / "cppp_gem.json"
    if not p.exists():
        return {"infra_projects": []}
    return json.loads(p.read_text(encoding="utf-8"))


@router.get("/portals/rera")
async def rera_last() -> dict:
    import json
    p = Path(__file__).resolve().parents[4] / "out" / "portal_outputs" / "rera_up.json"
    if not p.exists():
        return {"rera_projects": []}
    return json.loads(p.read_text(encoding="utf-8"))


@router.get("/history/{gatta_number}", response_model=AnalysisHistoryRecord)
async def history_detail(
    gatta_number: str,
    service: LandIntelligenceService = Depends(get_land_service),
) -> AnalysisHistoryRecord:
    record = service.load_history_record(gatta_number)
    if record is None:
        raise ValueError(f"No saved history found for gatta number {gatta_number}.")
    return record
