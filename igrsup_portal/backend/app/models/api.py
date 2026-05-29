from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class CoordinateInput(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class GeoJsonGeometry(BaseModel):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[Any]


class ParcelFeature(BaseModel):
    gatta_number: str
    village: str | None = None
    tehsil: str | None = None
    district: str = "Ayodhya"
    geometry: GeoJsonGeometry
    source: str
    source_confidence: float = Field(..., ge=0, le=1)


class InfrastructureProject(BaseModel):
    source: Literal["cppp", "gem"]
    project_id: str
    title: str
    authority: str | None = None
    category: str
    classification: str
    status: str
    coordinates: CoordinateInput
    distance_km: float = Field(..., ge=0)
    distance_band: Literal["adjacent", "near", "catchment", "regional"]
    influence_score: float = Field(..., ge=0, le=100)


class InfrastructureSummary(BaseModel):
    score: float = Field(..., ge=0, le=100)
    project_count: int = Field(..., ge=0)
    dominant_classification: str
    projects: list[InfrastructureProject]
    methodology: str


class BhunakshaRequest(BaseModel):
    coordinates: CoordinateInput


class BhunakshaResponse(BaseModel):
    status: str
    parcel: ParcelFeature
    scrape_metadata: dict[str, Any]


class BhulekhRequest(BaseModel):
    gatta_number: str = Field(..., min_length=1)
    village: str | None = None
    tehsil: str | None = None
    captcha_token: str | None = None

    @field_validator("gatta_number")
    @classmethod
    def normalize_gatta(cls, value: str) -> str:
        return value.strip()


class BhulekhRecord(BaseModel):
    gatta_number: str
    mutation_status: str
    bhoomi_prakar: str
    owner_name: str | None = None
    village: str | None = None
    tehsil: str | None = None
    source_language: str = "hi"
    confidence: float = Field(..., ge=0, le=1)


class BhulekhResponse(BaseModel):
    status: str
    record: BhulekhRecord
    scrape_metadata: dict[str, Any]


class ScoreRequest(BaseModel):
    coordinates: CoordinateInput | None = None
    gatta_number: str | None = None
    village: str | None = None
    tehsil: str | None = None
    captcha_token: str | None = None

    @field_validator("gatta_number")
    @classmethod
    def strip_optional_gatta(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class ScoreComponent(BaseModel):
    name: str
    score: float = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)
    reason: str


class ScoreResponse(BaseModel):
    status: str
    roci_final: float = Field(..., ge=0, le=100)
    zone_label: str
    parcel: ParcelFeature
    bhulekh: BhulekhRecord
    components: dict[str, ScoreComponent]
    scrape_metadata: dict[str, Any]


class AnalysisHistoryRecord(BaseModel):
    timestamp: str
    gatta_number: str
    village: str
    tehsil: str
    district: str
    latitude: str
    longitude: str
    roci_final: str
    infra_score: str
    risk_score: str
    confidence_score: str
    zone_label: str
    mutation_status: str
    owner_name: str
    source_confidence: str


class AnalysisHistoryListResponse(BaseModel):
    status: str
    records: list[AnalysisHistoryRecord]


class HealthResponse(BaseModel):
    status: str
    service: str
