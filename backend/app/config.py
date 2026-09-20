"""
IBVAP Backend Configuration
============================
All application configuration is loaded from environment variables or a .env file.
No sensitive values (credentials, secrets) should ever be hard-coded here.

Usage:
    from app.config import settings
    print(settings.log_level)
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All fields have safe defaults suitable for local development.
    Override via .env file or environment variables in production.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="IBVAP_",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_version: str = "v1"

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    # --- Storage ---
    storage_base_path: str = "./storage"
    evidence_retention_days: int = 30

    # --- Database (future) ---
    database_url: str | None = None  # Populated in Milestone 14
    sqlite_db_path: str = "m6_events.db"

    # --- Processing ---
    default_confidence_threshold: float = 0.5
    loitering_threshold_seconds: int = 10
    night_start_hour: int = 20
    night_end_hour: int = 6
    
    # Milestone 8: Night-Time Intelligence
    night_movement_threshold_minutes: int = 5
    night_luminance_threshold: float = 60.0
    night_hysteresis_frames: int = 30
    
    # Milestone 9: Automatic Number Plate Recognition (ANPR)
    anpr_detector_model_path: str = "yolov8n.pt" # Placeholder for plate model
    anpr_detector_confidence: float = 0.50
    anpr_min_vehicle_width: int = 100
    anpr_min_plate_width: int = 40
    anpr_consensus_threshold: int = 3
    anpr_enabled: bool = True
    
    max_cameras: int = 16
    processing_fps_limit: int = 25
    
    # Milestone 2: Frame Ingestion
    frame_buffer_capacity: int = 3
    playback_mode: str = "real_time"
    
    # Milestone 4: Tracking
    tracker_confidence_threshold: float = 0.65

    # Milestone 3: Object Detection
    detector_model_path: str = "yolov8s.pt"
    detector_confidence_threshold: float = 0.25
    detector_confidence_low_light: float = 0.20
    detector_confidence_night: float = 0.15
    detector_inference_size: int = 640
    detector_device: str = "auto"
    detector_enabled_classes: list[str] = ["person", "car", "motorcycle", "bus", "truck"]

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return upper

    @field_validator("playback_mode")
    @classmethod
    def validate_playback_mode(cls, v: str) -> str:
        allowed = {"real_time", "max_throughput"}
        if v not in allowed:
            raise ValueError(f"playback_mode must be one of {allowed}, got '{v}'")
        return v

    @field_validator("default_confidence_threshold")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("default_confidence_threshold must be between 0.0 and 1.0")
        return v

    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Singleton settings instance — import this throughout the application
settings = Settings()
