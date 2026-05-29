from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="ROCI Ayodhya Engine", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    allowed_origins: list[str] = Field(default=["http://localhost:3000"], alias="ALLOWED_ORIGINS")

    ayodhya_center_lat: float = Field(default=26.7999, alias="AYODHYA_CENTER_LAT")
    ayodhya_center_lng: float = Field(default=82.2042, alias="AYODHYA_CENTER_LNG")
    ayodhya_radius_km: float = Field(default=40, alias="AYODHYA_RADIUS_KM")
    ayodhya_min_lat: float = Field(default=26.60, alias="AYODHYA_MIN_LAT")
    ayodhya_max_lat: float = Field(default=27.00, alias="AYODHYA_MAX_LAT")
    ayodhya_min_lng: float = Field(default=81.95, alias="AYODHYA_MIN_LNG")
    ayodhya_max_lng: float = Field(default=82.45, alias="AYODHYA_MAX_LNG")

    bhunaksha_wfs_url: str = Field(alias="BHUNAKSHA_WFS_URL")
    bhunaksha_layer_name: str = Field(alias="BHUNAKSHA_LAYER_NAME")
    bhunaksha_wfs_version: str = Field(default="1.0.0", alias="BHUNAKSHA_WFS_VERSION")
    bhunaksha_bbox_buffer_degrees: float = Field(default=0.002, alias="BHUNAKSHA_BBOX_BUFFER_DEGREES")
    bhunaksha_request_timeout_seconds: int = Field(default=20, alias="BHUNAKSHA_REQUEST_TIMEOUT_SECONDS")
    bhunaksha_plot_info_url: str = Field(
        default="https://upbhunaksha.gov.in/bhunakshaserver/MapInfo/getPlotInfo",
        alias="BHUNAKSHA_PLOT_INFO_URL",
    )
    bhunaksha_max_retries: int = Field(default=3, alias="BHUNAKSHA_MAX_RETRIES")
    bhunaksha_request_sleep_seconds: float = Field(default=0.5, alias="BHUNAKSHA_REQUEST_SLEEP_SECONDS")
    bhulekh_base_url: str = Field(alias="BHULEKH_BASE_URL")
    bhulekh_timeout_seconds: int = Field(default=45, alias="BHULEKH_TIMEOUT_SECONDS")

    project_root: Path = Field(default=Path(__file__).resolve().parents[2], alias="PROJECT_ROOT")
    backend_root: Path = Field(default=Path(__file__).resolve().parents[1], alias="BACKEND_ROOT")
    data_dir: Path = Field(default=Path(__file__).resolve().parents[1] / "data", alias="DATA_DIR")
    docs_dir: Path = Field(default=Path(__file__).resolve().parents[1] / "docs", alias="DOCS_DIR")
    land_data_csv: Path = Field(default=Path(__file__).resolve().parents[1] / "data" / "land_data.csv", alias="LAND_DATA_CSV")
    parsed_land_data_csv: Path = Field(
        default=Path(__file__).resolve().parents[1] / "data" / "parsed_land_data.csv",
        alias="PARSED_LAND_DATA_CSV",
    )
    analysis_history_csv: Path = Field(
        default=Path(__file__).resolve().parents[1] / "data" / "analysis_history.csv",
        alias="ANALYSIS_HISTORY_CSV",
    )
    failed_plots_csv: Path = Field(default=Path(__file__).resolve().parents[1] / "data" / "failed_plots.csv", alias="FAILED_PLOTS_CSV")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                import json
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
