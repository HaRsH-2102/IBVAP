"""
IBVAP Domain — Camera
======================
Represents a physical or logical CCTV source.

A Camera is a persistent configuration entity — it describes a source of video
that the platform knows about. Whether the camera is currently streaming is
captured by the associated VideoStream object.

Architectural note:
    - Camera IDs must be unique across the platform.
    - Every downstream domain object (Frame, Detection, Track, Event) carries
      the camera_id to maintain full data lineage.
    - Camera credentials (stream URLs with passwords) must NEVER be stored
      directly in source code — they are loaded from environment/config.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CameraStatus(str, Enum):
    """Operational status of a camera as known to the platform."""

    ACTIVE = "ACTIVE"       # Camera is registered and streaming
    INACTIVE = "INACTIVE"   # Camera is registered but not streaming
    ERROR = "ERROR"         # Camera has encountered a connection/processing error
    UNKNOWN = "UNKNOWN"     # Status has not yet been determined


class Camera(BaseModel):
    """
    Represents a physical or logical CCTV camera source.

    This is a configuration/registration model — it describes what the platform
    knows about a camera, not the live state of its stream (see VideoStream for that).

    Attributes:
        camera_id: Unique identifier for this camera across the entire platform.
        name: Human-readable display name.
        location: Physical or logical location description (e.g., "North Gate", "Sector 7").
        stream_config: Stream source configuration. Should NOT contain raw credentials
            in source code — reference environment variable names or config keys instead.
        status: Current operational status.
        capabilities: Feature flags for this camera (e.g., ["infrared", "ptz"]).
            Used in future milestones to tailor processing per camera.
        configuration: Camera-specific processing overrides (FPS limit, confidence
            threshold, etc.). Keys/values are defined per milestone.
        zone_ids: IDs of Zone objects associated with this camera.
        virtual_line_ids: IDs of VirtualLine objects associated with this camera.

    Future:
        - Database persistence (Milestone 14)
        - Authentication/authorization on camera access
        - PTZ control integration
    """

    camera_id: str = Field(..., description="Unique camera identifier")
    name: str = Field(..., description="Human-readable camera name")
    location: str = Field(default="", description="Physical or logical location")
    stream_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Stream source configuration (no raw credentials in code)",
    )
    status: CameraStatus = Field(default=CameraStatus.UNKNOWN)
    capabilities: list[str] = Field(
        default_factory=list,
        description="Feature flags: 'infrared', 'ptz', 'audio', etc.",
    )
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-camera processing parameter overrides",
    )
    zone_ids: list[str] = Field(
        default_factory=list,
        description="IDs of associated Zone objects",
    )
    virtual_line_ids: list[str] = Field(
        default_factory=list,
        description="IDs of associated VirtualLine objects",
    )

    model_config = ConfigDict(use_enum_values=False)
