"""
IBVAP Domain — VirtualLine
===========================
Represents an operator-configured line used to detect crossing events.

Virtual lines enable direction-aware counting and crossing detection.
When a tracked object's trajectory crosses a configured line, the system
can determine whether the crossing was in an allowed or prohibited direction.

Architectural note:
    - VirtualLines are persistent configuration entities (database, Milestone 14).
    - Line evaluation is performed by the SpatialEngine (Layer 5).
    - Crossing detection requires trajectory history from the Track — this is
      why trajectories are stored in the Track domain model.
    - Direction control supports bidirectional lines (for counting) and
      unidirectional lines (for prohibited-direction events).

Future (Milestone 5+):
    - SpatialEngine.has_crossed_line(track, line) → CrossingResult
    - Direction analysis using trajectory delta
    - Counting per line per direction per time period
    - ANPR triggers on line crossing by vehicle
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.zone import Point


class Direction(str, Enum):
    """
    Crossing direction policy for a virtual line.

    The line defines two sides: A (left/above) and B (right/below).
    The direction policy controls which crossings generate events.
    """

    A_TO_B = "A_TO_B"      # Only crossings from A side to B side are flagged
    B_TO_A = "B_TO_A"      # Only crossings from B side to A side are flagged
    BOTH = "BOTH"           # All crossings are tracked (bidirectional counting)
    NONE = "NONE"           # Line exists for geometry reference only (no events)


class VirtualLine(BaseModel):
    """
    Represents an operator-defined line for crossing/direction detection.

    The line is defined by start and end points in pixel coordinates.
    The SpatialEngine determines which side of the line ("A" or "B") an object
    is on, and detects crossings by analyzing trajectory history.

    Attributes:
        line_id: Unique identifier.
        camera_id: The camera this line applies to.
        name: Human-readable name (e.g., "Entry Line North", "Perimeter Boundary").
        start: Line start point in pixel coordinates.
        end: Line end point in pixel coordinates.
        allowed_direction: Policy controlling which crossings generate events.
        active: Whether this line is active for event generation.
        configuration: Extensible line-specific settings.

    Future:
        - Counting statistics per direction per time window
        - ANPR trigger: activate plate reading on vehicle line-crossing
        - Speed estimation using line crossing timestamp + calibrated distance
    """

    line_id: str = Field(..., description="Unique virtual line identifier")
    camera_id: str = Field(..., description="Source camera identifier")
    name: str = Field(..., description="Human-readable line name")
    start: Point = Field(..., description="Line start point in pixel coordinates")
    end: Point = Field(..., description="Line end point in pixel coordinates")
    allowed_direction: Direction = Field(
        default=Direction.BOTH,
        description="Which crossing direction(s) generate events",
    )
    active: bool = Field(default=True, description="Whether line is active for event generation")
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible line-specific configuration",
    )
