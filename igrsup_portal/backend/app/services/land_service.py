from __future__ import annotations

import csv

from app.config import settings
from app.models.api import (
    AnalysisHistoryRecord,
    BhulekhRecord,
    BhulekhRequest,
    BhulekhResponse,
    BhunakshaRequest,
    BhunakshaResponse,
    ScoreRequest,
    ScoreResponse,
)
from app.scoring.engine import RociScoringEngine
from app.scrapers.bhulekh import BhulekhScraper
from app.scrapers.bhunaksha import BhunakshaScraper
from app.services.infrastructure_service import InfrastructureService
from app.services.storage_service import StorageService
from app.utils.logging import logger


class LandIntelligenceService:
    def __init__(self) -> None:
        self.bhunaksha_scraper = BhunakshaScraper()
        self.bhulekh_scraper = BhulekhScraper()
        self.infrastructure_service = InfrastructureService()
        self.storage_service = StorageService()
        self.scoring_engine = RociScoringEngine()

    async def fetch_bhunaksha(self, payload: BhunakshaRequest) -> BhunakshaResponse:
        return await self.bhunaksha_scraper.lookup(payload)

    async def fetch_bhulekh(self, payload: BhulekhRequest) -> BhulekhResponse:
        return await self.bhulekh_scraper.lookup(payload)

    async def score(self, payload: ScoreRequest) -> ScoreResponse:
        logger.info("Scoring Ayodhya parcel for gatta={} coordinates_present={}", payload.gatta_number, bool(payload.coordinates))

        if payload.coordinates:
            bhunaksha_response = await self.fetch_bhunaksha(BhunakshaRequest(coordinates=payload.coordinates))
            parcel = bhunaksha_response.parcel
            if payload.gatta_number:
                parcel = parcel.model_copy(
                    update={
                        "gatta_number": payload.gatta_number,
                        "village": payload.village or parcel.village,
                        "tehsil": payload.tehsil or parcel.tehsil,
                    }
                )
        elif payload.gatta_number:
            parcel = self.bhunaksha_scraper._fallback_feature(26.7999, 82.2042)
            parcel = parcel.model_copy(
                update={
                    "gatta_number": payload.gatta_number,
                    "village": payload.village or parcel.village,
                    "tehsil": payload.tehsil or parcel.tehsil,
                }
            )
        else:
            raise ValueError("Either coordinates or gatta_number must be supplied.")

        bhulekh_response = await self.fetch_bhulekh(
            BhulekhRequest(
                gatta_number=payload.gatta_number or parcel.gatta_number,
                village=payload.village or parcel.village,
                tehsil=payload.tehsil or parcel.tehsil,
                captcha_token=payload.captcha_token,
            )
        )

        bhulekh_record = self._enrich_from_parsed_csv(parcel.gatta_number, bhulekh_response.record)

        infrastructure_summary = None
        if payload.coordinates:
            infrastructure_summary = await self.infrastructure_service.analyze(payload.coordinates)

        components = self.scoring_engine.score(parcel, bhulekh_record, infrastructure_summary)
        roci_final = self.scoring_engine.aggregate(components)
        zone_label = self.scoring_engine.zone_label(roci_final)

        scrape_metadata = {
            "bhunaksha": bhunaksha_response.scrape_metadata if payload.coordinates else {"source": "gatta_only_flow"},
            "bhulekh": bhulekh_response.scrape_metadata,
            "infrastructure": infrastructure_summary.model_dump() if infrastructure_summary else {"source": "not_run"},
        }

        response = ScoreResponse(
            status="OK",
            roci_final=roci_final,
            zone_label=zone_label,
            parcel=parcel,
            bhulekh=bhulekh_record,
            components=components,
            scrape_metadata=scrape_metadata,
        )
        self._persist_analysis_history(response, payload)
        return response

    def load_history(self, limit: int = 50) -> list[AnalysisHistoryRecord]:
        rows = self.storage_service.load_analysis_history(limit=limit)
        return [AnalysisHistoryRecord(**row) for row in rows]

    def load_history_record(self, gatta_number: str) -> AnalysisHistoryRecord | None:
        row = self.storage_service.load_by_gatta_number(gatta_number)
        return AnalysisHistoryRecord(**row) if row else None

    def export_history_path(self) -> str:
        return str(self.storage_service.export_path())

    def _persist_analysis_history(self, response: ScoreResponse, payload: ScoreRequest) -> None:
        self.storage_service.save_analysis_result(
            {
                "gatta_number": response.parcel.gatta_number,
                "village": response.parcel.village or response.bhulekh.village or "",
                "tehsil": response.parcel.tehsil or response.bhulekh.tehsil or "",
                "district": response.parcel.district,
                "latitude": payload.coordinates.lat if payload.coordinates else "",
                "longitude": payload.coordinates.lng if payload.coordinates else "",
                "roci_final": response.roci_final,
                "infra_score": response.components.get("infra_score").score if response.components.get("infra_score") else "",
                "risk_score": response.components.get("risk_score").score if response.components.get("risk_score") else "",
                "confidence_score": response.components.get("confidence_score").score if response.components.get("confidence_score") else "",
                "zone_label": response.zone_label,
                "mutation_status": response.bhulekh.mutation_status,
                "owner_name": response.bhulekh.owner_name or "",
                "source_confidence": response.parcel.source_confidence,
            }
        )

    def _enrich_from_parsed_csv(self, gatta_number: str, record: BhulekhRecord) -> BhulekhRecord:
        bhulekh_record = record
        parsed_path = settings.parsed_land_data_csv
        if not parsed_path.exists():
            return bhulekh_record

        try:
            with parsed_path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if row.get("plot_number") != gatta_number:
                        continue
                    owner_name = row.get("owner_name") or getattr(bhulekh_record, "owner_name", None)
                    mutation_status = row.get("mutation_status") or getattr(bhulekh_record, "mutation_status", "")
                    return bhulekh_record.model_copy(
                        update={
                            "owner_name": owner_name,
                            "mutation_status": mutation_status or getattr(bhulekh_record, "mutation_status", ""),
                        }
                    )
        except Exception as exc:
            logger.warning("Failed to enrich Bhulekh record from parsed CSV for gatta={}: {}", gatta_number, exc)

        return bhulekh_record
