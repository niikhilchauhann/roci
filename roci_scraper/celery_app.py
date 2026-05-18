from __future__ import annotations

from celery import Celery

app = Celery("roci_scraper", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")
app.conf.update(task_track_started=True, worker_prefetch_multiplier=1)
