"""
IBVAP Domain — Zone
====================
Represents an operator-configured area on a camera's field of view.

Zones are the primary mechanism for spatial intelligence. An operator draws
polygons on a camera view, classifies them, and the system evaluates whether
tracked objects are inside those zones.

Architectural note:
    - Zones are persistent configuration entities (stored in database, Milestone 14).
    - Zone geometry is defined in pixel coordinates for a specific camera.
    - Zone evaluation is performed by the SpatialEngine (Layer 5) — this model
      only holds the configuration.
    - All zone logic operates on Track objects, not directly on AI model outputs.

Future (Milestone 5+):
    - SpatialEngine.is_inside_zone(track, zone) → bool
    - Time-of-day activation rules
    - Per-zone object class filters (e.g., "alert only on PERSON, not vehicles")
    - Zone sensitivity/confidence thresholds
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ZoneType(str, Enum):
    """Classification of a zone's security function."""

    NORMAL = "NORMAL"           # Standard monitoring area
    RESTRICTED = "RESTRICTED"   # Unauthorized access triggers alert
    MONITORING = "MONITORING"   # Passive observation, analytics only
    ENTRY = "ENTRY"             # Designated entry point
    EXIT = "EXIT"               # Designated exit point


class Point(BaseModel):
    """A 2D point in pixel coordinates."""

    x: float = Field(..., description="Horizontal position in pixels")
    y: float = Field(..., description="Vertical position in pixels")


class Zone(BaseModel):
    """
    Represents an operator-defined area on a camera's field of view.

    The geometry is a polygon defined by vertices in pixel coordinates.
    Zone evaluation (containment, entry/exit detection) is performed by
    the SpatialEngine using the geometry stored here.

    Attributes:
        zone_id: Unique identifier for this zone.
        camera_id: The camera this zone applies to.
        name: Human-readable name (e.g., "Restricted Zone A", "Checkpoint 3").
        zone_type: Security classification of this zone.
        geometry: Ordered polygon vertices. Must have at least 3 points.
        active: Whether this zone is currently active for event generation.
        configuration: Extensible per-zone settings (object class filters,
            time rules, dwell thresholds, etc.).

    Future:
        - Persistent storage via ORM (Milestone 14)
        - Time-based activation rules
        - Object class filtering per zone
        - Zone versioning for audit trail
    """

    zone_id: str = Field(..., description="Unique zone identifier")
    camera_id: str = Field(..., description="Source camera identifier")
    name: str = Field(..., description="Human-readable zone name")
    zone_type: ZoneType = Field(default=ZoneType.NORMAL)
    geometry: list[Point] = Field(
        default_factory=list,
        description="Ordered polygon vertices in pixel coordinates (minimum 3 points)",
    )
    active: bool = Field(default=True, description="Whether zone is active for event generation")
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible zone-specific configuration",
    )

    def is_valid_polygon(self) -> bool:
        """Returns True if geometry has at least 3 vertices to form a polygon."""
        return len(self.geometry) >= 3
