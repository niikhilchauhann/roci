from __future__ import annotations

from pathlib import Path
from .celery_app import app
from .main import run_pipeline


@app.task(name="roci.run_pipeline")
def run_pipeline_task(lat: float, lng: float, area_sqft: float, gatta_number: str | None = None, zone_type: str = "urban_expansion", output_dir: str = "out"):
    return run_pipeline(lat, lng, area_sqft, gatta_number, zone_type, Path(output_dir))
