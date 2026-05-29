from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.utils.logging import logger

ANALYSIS_HISTORY_HEADERS = [
    "timestamp",
    "gatta_number",
    "village",
    "tehsil",
    "district",
    "latitude",
    "longitude",
    "roci_final",
    "infra_score",
    "risk_score",
    "confidence_score",
    "zone_label",
    "mutation_status",
    "owner_name",
    "source_confidence",
]


class StorageService:
    def __init__(self) -> None:
        self.history_path = settings.analysis_history_csv
        self._ensure_history_file()

    def _ensure_history_file(self) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if self.history_path.exists() and self.history_path.stat().st_size > 0:
            return

        with self.history_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=ANALYSIS_HISTORY_HEADERS)
            writer.writeheader()
        logger.info("Initialized analysis history CSV at {}", self.history_path)

    def save_analysis_result(self, result: dict[str, Any]) -> None:
        self._ensure_history_file()
        row = {header: "" for header in ANALYSIS_HISTORY_HEADERS}
        row.update(
            {
                "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                "gatta_number": result.get("gatta_number") or "",
                "village": result.get("village") or "",
                "tehsil": result.get("tehsil") or "",
                "district": result.get("district") or "",
                "latitude": result.get("latitude") or "",
                "longitude": result.get("longitude") or "",
                "roci_final": result.get("roci_final") or "",
                "infra_score": result.get("infra_score") or "",
                "risk_score": result.get("risk_score") or "",
                "confidence_score": result.get("confidence_score") or "",
                "zone_label": result.get("zone_label") or "",
                "mutation_status": result.get("mutation_status") or "",
                "owner_name": result.get("owner_name") or "",
                "source_confidence": result.get("source_confidence") or "",
            }
        )

        with self.history_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=ANALYSIS_HISTORY_HEADERS)
            writer.writerow(row)

        logger.info("Persisted analysis history row for gatta={} score={}", row["gatta_number"], row["roci_final"])

    def load_analysis_history(self, limit: int = 20) -> list[dict[str, str]]:
        self._ensure_history_file()
        with self.history_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]

        rows.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
        logger.info("Loaded {} analysis history rows", min(limit, len(rows)))
        return rows[:limit]

    def load_by_gatta_number(self, gatta_number: str) -> dict[str, str] | None:
        if not gatta_number:
            return None

        self._ensure_history_file()
        with self.history_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader if row.get("gatta_number") == gatta_number]

        if not rows:
            logger.warning("No persisted history found for gatta={}", gatta_number)
            return None

        rows.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
        logger.info("Loaded persisted history record for gatta={}", gatta_number)
        return rows[0]

    def export_path(self) -> Path:
        self._ensure_history_file()
        return self.history_path
