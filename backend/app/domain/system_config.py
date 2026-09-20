"""
IBVAP Domain — SystemConfiguration
=====================================
Represents the global application configuration model as a domain concept.

This is the typed domain representation of the application's configuration state.
It is derived from the Settings model (app/config.py) and passed through the
system where components need to read configuration at runtime.

Architectural note:
    - SystemConfiguration is a read-only snapshot — it should not be mutated at runtime.
    - Per-camera overrides exist on the Camera model's configuration field.
    - Surveillance rule parameters (loitering_threshold, night hours, etc.) will
      eventually be stored in the database and per-zone/camera, not just globally.
    - This model is also used as the response schema for the /api/v1/system/config endpoint.

Future:
    - Per-camera configuration overrides (Milestone 16)
    - Dynamic reload without server restart
    - Configuration validation pipeline
    - Admin UI for configuration management
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SystemConfiguration(BaseModel):
    """
    Global application configuration as a typed domain model.

    This is the unified view of all tunable system parameters.
    The values are loaded from environment variables via the Settings model
    and exposed through the API for operator visibility.

    Sensitive values (database URL, camera credentials) are NEVER included here.

    Attributes:
        log_level: Application logging verbosity.
        api_version: Current API version string.
        storage_base_path: Root directory for local file storage (evidence, etc.).
        evidence_retention_days: Default evidence retention period.
        default_confidence_threshold: Minimum AI detection confidence accepted.
        loitering_threshold_seconds: Default minimum dwell time for loitering detection.
        night_start_hour: Hour (0-23) when "night" begins for night-movement rules.
        night_end_hour: Hour (0-23) when "night" ends.
        max_cameras: Maximum number of cameras the platform will manage simultaneously.
        processing_fps_limit: Maximum frame rate for video processing per camera.

    Future:
        - Per-camera threshold overrides
        - Zone-specific loitering thresholds
        - Risk scoring weights
        - Alert escalation timeouts
    """

    log_level: str = Field(default="INFO")
    api_version: str = Field(default="v1")
    anpr_enabled: bool = True
    anpr_queue_size: int = 50
    anpr_worker_count: int = 1
    anpr_detector_confidence: float = 0.50
    anpr_detector_model_path: str = "best.pt"
    anpr_consensus_threshold: int = 3
    anpr_min_vehicle_width: int = 100
    anpr_min_plate_width: int = 40
    anpr_ocr_timeout_ms: int = 2000
    anpr_processing_timeout_ms: int = 5000
    
    # Evidence (M10)
    evidence_enabled: bool = True
    evidence_queue_capacity: int = 50
    trajectory_snapshot_points: int = 30
    evidence_exact_tolerance_ms: int = 80
    evidence_max_delta_ms: int = 500
    max_evidence_retries: int = 1
    evidence_image_format: str = "JPEG"
    evidence_image_quality: int = 90
    
    # Incident Clip (M11)
    incident_clip_enabled: bool = True
    pre_event_seconds: int = 5
    post_event_seconds: int = 5
    minimum_clip_duration_seconds: int = 2
    maximum_clip_duration_seconds: int = 30
    clip_event_frame_tolerance_ms: int = 100
    clip_max_seek_error_ms: int = 200
    clip_queue_capacity: int = 10
    clip_worker_count: int = 1
    max_clip_retries: int = 1
    clip_format: str = "mp4"
    thumbnail_enabled: bool = True
    clip_retention_enabled: bool = False
    clip_retention_days: int = 30
    minimum_free_disk_gb: int = 5
    
    storage_base_path: str = Field(default="./storage")
    evidence_retention_days: int = Field(default=30)
    default_confidence_threshold: float = Field(default=0.5)
    loitering_threshold_seconds: int = Field(default=60)
    night_start_hour: int = Field(default=20, ge=0, le=23)
    night_end_hour: int = Field(default=6, ge=0, le=23)
    max_cameras: int = Field(default=16, ge=1)
    processing_fps_limit: int = Field(default=25, ge=1)
    frame_buffer_capacity: int = Field(
        default=3, 
        ge=1, 
        le=30, 
        description="Max frames buffered per camera to absorb processing spikes"
    )
    playback_mode: str = Field(
        default="real_time",
        description="'real_time' (paced) or 'max_throughput' (unpaced benchmarking)"
    )

    # Milestone 3: Object Detection
    detector_model_path: str = Field(
        default="yolov8n.pt",
        description="Path or name of the pretrained object detection model (e.g., yolov8n.pt)"
    )
    detector_confidence_threshold: float = Field(
        default=0.25,
        ge=0.01,
        le=1.0,
        description="Minimum confidence score for a valid detection"
    )
    detector_inference_size: int = Field(
        default=640,
        ge=320,
        description="Input resolution for the model (square assumed). e.g., 640 or 1280"
    )
    detector_device: str = Field(
        default="auto",
        description="'auto', 'cuda', or 'cpu'"
    )
    detector_enabled_classes: list[str] = Field(
        default=["person", "car", "motorcycle", "bus", "truck"],
        description="List of internal semantic classes to preserve from the detector output"
    )

    @classmethod
    def from_settings(cls, settings: object) -> "SystemConfiguration":
        """
        Build a SystemConfiguration from the application Settings object.
        This avoids tight coupling between domain models and the settings module.
        """
        return cls(
            log_level=getattr(settings, "log_level", "INFO"),
            api_version=getattr(settings, "api_version", "v1"),
            storage_base_path=getattr(settings, "storage_base_path", "./storage"),
            evidence_retention_days=getattr(settings, "evidence_retention_days", 30),
            default_confidence_threshold=getattr(settings, "default_confidence_threshold", 0.5),
            loitering_threshold_seconds=getattr(settings, "loitering_threshold_seconds", 60),
            night_start_hour=getattr(settings, "night_start_hour", 20),
            night_end_hour=getattr(settings, "night_end_hour", 6),
            max_cameras=getattr(settings, "max_cameras", 16),
            processing_fps_limit=getattr(settings, "processing_fps_limit", 25),
            frame_buffer_capacity=getattr(settings, "frame_buffer_capacity", 3),
            playback_mode=getattr(settings, "playback_mode", "real_time"),
            detector_model_path=getattr(settings, "detector_model_path", "yolov8n.pt"),
            detector_confidence_threshold=getattr(settings, "detector_confidence_threshold", 0.25),
            detector_inference_size=getattr(settings, "detector_inference_size", 640),
            detector_device=getattr(settings, "detector_device", "auto"),
            detector_enabled_classes=getattr(settings, "detector_enabled_classes", ["person", "car", "motorcycle", "bus", "truck"]),
            incident_clip_enabled=getattr(settings, "incident_clip_enabled", True),
            pre_event_seconds=getattr(settings, "pre_event_seconds", 5),
            post_event_seconds=getattr(settings, "post_event_seconds", 5),
            minimum_clip_duration_seconds=getattr(settings, "minimum_clip_duration_seconds", 2),
            maximum_clip_duration_seconds=getattr(settings, "maximum_clip_duration_seconds", 30),
            clip_event_frame_tolerance_ms=getattr(settings, "clip_event_frame_tolerance_ms", 100),
            clip_max_seek_error_ms=getattr(settings, "clip_max_seek_error_ms", 200),
            clip_queue_capacity=getattr(settings, "clip_queue_capacity", 10),
            clip_worker_count=getattr(settings, "clip_worker_count", 1),
            max_clip_retries=getattr(settings, "max_clip_retries", 1),
            clip_format=getattr(settings, "clip_format", "mp4"),
            thumbnail_enabled=getattr(settings, "thumbnail_enabled", True),
            clip_retention_enabled=getattr(settings, "clip_retention_enabled", False),
            clip_retention_days=getattr(settings, "clip_retention_days", 30),
            minimum_free_disk_gb=getattr(settings, "minimum_free_disk_gb", 5),
        )
