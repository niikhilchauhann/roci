from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from typing import Any

import httpx
import requests
from shapely.geometry import Point, mapping, shape
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.models.api import BhunakshaRequest, BhunakshaResponse, GeoJsonGeometry, ParcelFeature
from app.utils.gis import assert_within_ayodhya
from app.utils.logging import logger


class BhunakshaScraper:
    def __init__(self) -> None:
        self.base_url = settings.bhunaksha_wfs_url
        self.layer_name = settings.bhunaksha_layer_name
        self.wfs_version = settings.bhunaksha_wfs_version
        self.bbox_buffer = settings.bhunaksha_bbox_buffer_degrees
        self.request_timeout_seconds = settings.bhunaksha_request_timeout_seconds
        self.plot_info_url = settings.bhunaksha_plot_info_url
        self.max_retries = settings.bhunaksha_max_retries
        self.request_sleep_seconds = settings.bhunaksha_request_sleep_seconds
        self.village_catalog_path = settings.backend_root / "app" / "ref_data" / "ayodhya_villages.csv"

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def _fetch_wfs(self, lat: float, lng: float) -> dict[str, Any]:
        params = self._build_wfs_params(lat, lng)
        logger.info("Fetching Bhunaksha WFS data for lat={}, lng={}, layer={}", lat, lng, self.layer_name)
        async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()

    def _build_wfs_params(self, lat: float, lng: float) -> dict[str, str]:
        bbox = self._bbox_for_point(lat, lng)
        return {
            "service": "WFS",
            "version": self.wfs_version,
            "request": "GetFeature",
            "typeName": self.layer_name,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            "bbox": bbox,
        }

    def _bbox_for_point(self, lat: float, lng: float) -> str:
        buffer_size = self.bbox_buffer
        return f"{lng - buffer_size},{lat - buffer_size},{lng + buffer_size},{lat + buffer_size},EPSG:4326"

    async def lookup(self, payload: BhunakshaRequest) -> BhunakshaResponse:
        lat = payload.coordinates.lat
        lng = payload.coordinates.lng
        assert_within_ayodhya(lat, lng)

        try:
            data = await self._fetch_wfs(lat, lng)
            feature, selection_metadata = self._select_feature(data, lat, lng)
            metadata = {
                "source": "bhunaksha_wfs",
                "endpoint": self.base_url,
                "layer_name": self.layer_name,
                "request_params": self._build_wfs_params(lat, lng),
                "feature_count": len(data.get("features", [])),
                "fallback_used": False,
                **selection_metadata,
            }
            return BhunakshaResponse(status="OK", parcel=feature, scrape_metadata=metadata)
        except Exception as exc:
            logger.warning("Bhunaksha WFS lookup failed, using local fallback: {}", exc)
            feature = self._fallback_feature(lat, lng)
            metadata = {
                "source": "bhunaksha_fallback",
                "endpoint": self.base_url,
                "layer_name": self.layer_name,
                "request_params": self._build_wfs_params(lat, lng),
                "fallback_used": True,
                "error": str(exc),
            }
            return BhunakshaResponse(status="OK", parcel=feature, scrape_metadata=metadata)

    def _select_feature(self, data: dict[str, Any], lat: float, lng: float) -> tuple[ParcelFeature, dict[str, Any]]:
        features = data.get("features", [])
        target = Point(lng, lat)
        candidates: list[tuple[float, dict[str, Any], Any]] = []

        for item in features:
            geometry = item.get("geometry")
            if not geometry:
                continue

            normalized_geometry = self._normalize_geometry(geometry)
            parcel_shape = shape(normalized_geometry)
            if parcel_shape.is_empty:
                continue

            distance = 0.0 if parcel_shape.contains(target) or parcel_shape.touches(target) else parcel_shape.distance(target)
            candidates.append((distance, item, normalized_geometry))

        if not candidates:
            fallback = self._fallback_feature(lat, lng)
            return fallback, {
                "selection_strategy": "fallback_no_candidate",
                "selection_distance": None,
            }

        candidates.sort(key=lambda candidate: candidate[0])
        best_distance, best_item, normalized_geometry = candidates[0]
        props = best_item.get("properties", {})
        selected_feature = ParcelFeature(
            gatta_number=self._extract_gatta_number(props),
            village=self._extract_property(props, ["village", "village_name", "mauja"]),
            tehsil=self._extract_property(props, ["tehsil", "tehsil_name", "tahsil"]),
            geometry=GeoJsonGeometry(**normalized_geometry),
            source="bhunaksha_wfs",
            source_confidence=self._confidence_from_distance(best_distance),
        )
        metadata = {
            "selection_strategy": "nearest_geometry",
            "selection_distance": round(best_distance, 8),
            "matched_properties": sorted(props.keys()),
        }
        return selected_feature, metadata

    def _normalize_geometry(self, geometry: dict[str, Any]) -> dict[str, Any]:
        normalized = mapping(shape(geometry))
        return {
            "type": normalized["type"],
            "coordinates": normalized["coordinates"],
        }

    def _extract_gatta_number(self, props: dict[str, Any]) -> str:
        value = self._extract_property(
            props,
            ["gatta_no", "gatta_number", "plot_no", "plot_number", "khasra_no", "survey_no"],
        )
        return str(value or "UNKNOWN")

    def _extract_property(self, props: dict[str, Any], candidates: list[str]) -> str | None:
        lowered = {str(key).lower(): value for key, value in props.items()}
        for candidate in candidates:
            if candidate.lower() in lowered and lowered[candidate.lower()] not in (None, ""):
                return str(lowered[candidate.lower()])
        return None

    def _confidence_from_distance(self, distance: float) -> float:
        if distance == 0:
            return 0.95
        if distance <= 0.0002:
            return 0.84
        if distance <= 0.0007:
            return 0.72
        return 0.61

    def _fallback_feature(self, lat: float, lng: float) -> ParcelFeature:
        offset = 0.0007
        geometry = GeoJsonGeometry(
            type="Polygon",
            coordinates=[[
                [lng - offset, lat - offset],
                [lng + offset, lat - offset],
                [lng + offset, lat + offset],
                [lng - offset, lat + offset],
                [lng - offset, lat - offset],
            ]],
        )
        return ParcelFeature(
            gatta_number=f"AYO-{int(abs(lat * 1000))}-{int(abs(lng * 1000))}",
            village="Ayodhya Demo Village",
            tehsil="Sadar",
            geometry=geometry,
            source="bhunaksha_fallback",
            source_confidence=0.58,
        )

    def get_villages(self, district: str = "Ayodhya", tehsil: str | None = None) -> list[dict[str, str]]:
        villages: list[dict[str, str]] = []
        district_normalized = district.strip().lower()
        tehsil_normalized = tehsil.strip().lower() if tehsil else None

        with self.village_catalog_path.open(mode="r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row["district"].strip().lower() != district_normalized:
                    continue
                if tehsil_normalized and row["tehsil"].strip().lower() != tehsil_normalized:
                    continue
                villages.append(row)

        logger.info("Loaded {} villages for district={} tehsil={}", len(villages), district, tehsil or "ALL")
        return villages

    def generate_gis_code(self, district: str, tehsil: str, village: str) -> str:
        district_normalized = district.strip().lower()
        tehsil_normalized = tehsil.strip().lower()
        village_normalized = village.strip().lower()

        for row in self.get_villages(district=district, tehsil=tehsil):
            if row["district"].strip().lower() == district_normalized and row["tehsil"].strip().lower() == tehsil_normalized and row["village"].strip().lower() == village_normalized:
                logger.info("Resolved GIS code {} for village={} tehsil={} district={}", row["gis_code"], village, tehsil, district)
                return row["gis_code"]

        raise ValueError(f"No GIS code mapping found for district={district}, tehsil={tehsil}, village={village}.")

    def get_plot_info(self, gis_code: str, plot_no: str | int) -> dict[str, Any]:
        payload = {
            "gisCode": str(gis_code),
            "plotNo": str(plot_no),
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("Fetching plot info for gis_code={} plot_no={} attempt={}/{}", gis_code, plot_no, attempt, self.max_retries)
                response = requests.post(self.plot_info_url, json=payload, timeout=self.request_timeout_seconds)
                response.raise_for_status()
                clean_text = re.sub(r"\s+", " ", response.text).strip()
                return {
                    "plot_number": str(plot_no),
                    "status_code": response.status_code,
                    "response_text": clean_text,
                    "success": True,
                    "attempts": attempt,
                }
            except requests.exceptions.Timeout as exc:
                logger.warning("Timeout while fetching plot {} on attempt {}/{}: {}", plot_no, attempt, self.max_retries, exc)
                if attempt == self.max_retries:
                    return self._failed_plot_result(plot_no, exc, attempt)
                time.sleep(self.request_sleep_seconds)
            except requests.exceptions.RequestException as exc:
                logger.warning("Request failed for plot {} on attempt {}/{}: {}", plot_no, attempt, self.max_retries, exc)
                if attempt == self.max_retries:
                    return self._failed_plot_result(plot_no, exc, attempt)
                time.sleep(self.request_sleep_seconds)

        return self._failed_plot_result(plot_no, RuntimeError("Unknown plot info failure"), self.max_retries)

    def get_plot_by_number(self, gis_code: str, plot_no: str | int) -> dict[str, Any]:
        plot_info = self.get_plot_info(gis_code, plot_no)
        if not plot_info["success"]:
            return plot_info

        parsed = self.parse_plot_info(plot_info["response_text"])
        return {
            **plot_info,
            **parsed,
        }

    def parse_plot_info(self, response_text: str) -> dict[str, str]:
        plot_match = re.search(r"Plot No:\s*([^\s]+)", response_text)
        khata_match = re.search(r"Khata No:\s*([0-9A-Za-z]+)", response_text)
        area_match = re.search(r"Area\s*:\s*([0-9.]+)", response_text)
        owner_match = re.search(r"नाम\s*:\s*(.*?)(?:संरक्षक|निवास|Owner Details|Order Description|$)", response_text)

        return {
            "plot_number": plot_match.group(1).strip() if plot_match else "Not Found",
            "khata_number": khata_match.group(1).strip() if khata_match else "Not Found",
            "owner_name": owner_match.group(1).strip() if owner_match else "Not Found",
            "area": area_match.group(1).strip() if area_match else "Not Found",
        }

    def export_rows_to_csv(self, file_path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
        with file_path.open(mode="w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Exported {} rows to {}", len(rows), file_path)

    def _failed_plot_result(self, plot_no: str | int, exc: Exception, attempts: int) -> dict[str, Any]:
        return {
            "plot_number": str(plot_no),
            "status_code": None,
            "response_text": "",
            "success": False,
            "attempts": attempts,
            "error": str(exc),
        }
