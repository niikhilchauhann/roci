from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from pathlib import Path

from roci_scraper.main import run_pipeline


default_args = {"owner": "roci", "retries": 1}

with DAG(
    dag_id="roci_score_pipeline",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["roci", "demo"],
) as dag:

    def _score():
        return run_pipeline(26.7954, 82.1942, 174240, "374/1-A", "urban_expansion", Path("/tmp/roci_out"))

    run_score = PythonOperator(task_id="run_score", python_callable=_score)
