from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

class InfraProject(BaseModel):
    type_weight: float = Field(ge=0, le=1)
    distance_km: float = Field(ge=0)
    stage_multiplier: float = Field(ge=0, le=1)
    title: str = ''
    org: str = ''

class ReraProject(BaseModel):
    scale_weight: float = Field(ge=-0.3, le=1)
    distance_km: float = Field(ge=0)
    stage_multiplier: float = Field(ge=-0.3, le=1)
    name: str = ''
    reg_number: str = ''

class ScrapeMetadata(BaseModel):
    scraped_at: str
    portals_ok: List[str] = Field(default_factory=list)
    portals_failed: List[str] = Field(default_factory=list)
    gatta_number: Optional[str] = None
    lat: float
    lng: float
    area_sqft: float

class ScoreInput(BaseModel):
    model_config = ConfigDict(extra='allow')
    lat: float
    lng: float
    area_sqft: float
    gatta_number: Optional[str] = None
    zone_type: str = 'urban_expansion'
    lambda_decay: float = 0.15
    mutation_status: str = 'CLEAR'
    clu_current: int = 2
    clu_permitted: int = 7
    months_since_clu_change: int = 0
    far_subject: float = 1.5
    far_benchmark: float = 1.5
    clu_risk_flag: int = 0
    clu_pending_flag: int = 0
    zoning_flag: int = 0
    n_current: int = 0
    n_previous: int = 0
    mu_district: float = 0.0
    sigma_district: float = 1.0
    p_current: float = 0.0
    p_previous: float = 0.0
    infra_projects: List[InfraProject] = Field(default_factory=list)
    rera_projects: List[ReraProject] = Field(default_factory=list)
    portals_scraped: int = 5
    portals_required: int = 5
    hours_since_scrape: float = 0.0
    conflicts: int = 0
    validation_pairs: int = 2
    scrape_metadata: Optional[ScrapeMetadata] = None

    @field_validator('mutation_status')
    @classmethod
    def validate_mutation(cls, v: str) -> str:
        allowed = {'CLEAR', 'PENDING', 'NOT_INIT', 'DISPUTED', 'UNKNOWN'}
        if v not in allowed:
            return 'UNKNOWN'
        return v

    @field_validator('zone_type')
    @classmethod
    def validate_zone_type(cls, v: str) -> str:
        return v or 'urban_expansion'
