from __future__ import annotations

import time
from typing import Any

from app.config import settings
from app.scrapers.bhunaksha import BhunakshaScraper
from app.utils.logging import logger


class BhunakshaDemoService:
    def __init__(self) -> None:
        self.scraper = BhunakshaScraper()
        self.land_data_csv = settings.land_data_csv
        self.parsed_land_data_csv = settings.parsed_land_data_csv
        self.failed_plots_csv = settings.failed_plots_csv

    def run(
        self,
        district: str,
        tehsil: str,
        village: str,
        plot_start: int,
        plot_end: int,
    ) -> dict[str, Any]:
        villages = self.scraper.get_villages(district=district, tehsil=tehsil)
        gis_code = self.scraper.generate_gis_code(district=district, tehsil=tehsil, village=village)

        raw_rows: list[dict[str, Any]] = []
        parsed_rows: list[dict[str, Any]] = []
        failed_rows: list[dict[str, Any]] = []

        logger.info(
            "Starting Bhunaksha demo flow district={} tehsil={} village={} gis_code={} plots={}..{} villages_found={}",
            district,
            tehsil,
            village,
            gis_code,
            plot_start,
            plot_end,
            len(villages),
        )

        for plot_number in range(plot_start, plot_end + 1):
            plot_result = self.scraper.get_plot_by_number(gis_code=gis_code, plot_no=plot_number)

            if plot_result["success"] and "Khata No" in plot_result["response_text"]:
                raw_rows.append(
                    {
                        "plot_number": plot_result["plot_number"],
                        "status_code": plot_result["status_code"],
                        "response_text": plot_result["response_text"],
                    }
                )
                parsed_rows.append(
                    {
                        "plot_number": plot_result["plot_number"],
                        "khata_number": plot_result.get("khata_number", "Not Found"),
                        "owner_name": plot_result.get("owner_name", "Not Found"),
                        "area": plot_result.get("area", "Not Found"),
                    }
                )
                logger.info("Successful plot {} khata={} owner={} area={}", plot_result["plot_number"], plot_result.get("khata_number"), plot_result.get("owner_name"), plot_result.get("area"))
            elif not plot_result["success"]:
                failed_rows.append(
                    {
                        "plot_number": plot_result["plot_number"],
                        "error": plot_result.get("error", "Unknown error"),
                        "attempts": plot_result.get("attempts", 0),
                    }
                )
                logger.warning("Failed plot {} after {} attempts", plot_result["plot_number"], plot_result.get("attempts", 0))
            else:
                failed_rows.append(
                    {
                        "plot_number": plot_result["plot_number"],
                        "error": "Plot response did not contain Khata No marker",
                        "attempts": plot_result.get("attempts", 0),
                    }
                )
                logger.warning("Skipped plot {} because response did not contain parcel marker", plot_result["plot_number"])

            time.sleep(self.scraper.request_sleep_seconds)

        self.scraper.export_rows_to_csv(
            self.land_data_csv,
            ["plot_number", "status_code", "response_text"],
            raw_rows,
        )
        self.scraper.export_rows_to_csv(
            self.parsed_land_data_csv,
            ["plot_number", "khata_number", "owner_name", "area"],
            parsed_rows,
        )
        self.scraper.export_rows_to_csv(
            self.failed_plots_csv,
            ["plot_number", "error", "attempts"],
            failed_rows,
        )

        return {
            "district": district,
            "tehsil": tehsil,
            "village": village,
            "gis_code": gis_code,
            "villages_loaded": len(villages),
            "plots_requested": (plot_end - plot_start) + 1,
            "successful_plots": len(raw_rows),
            "failed_plots": len(failed_rows),
            "land_data_csv": str(self.land_data_csv),
            "parsed_land_data_csv": str(self.parsed_land_data_csv),
            "failed_plots_csv": str(self.failed_plots_csv),
        }
