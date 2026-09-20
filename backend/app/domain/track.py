"""
IBVAP Domain — Track
=====================
Represents the persistent temporal identity of a detected object across frames.

While a Detection is a snapshot ("I see a person in frame 42"), a Track is a
living identity ("Object #7 has been visible for 12 seconds and is moving north").

Architectural note:
    - Tracks are produced ONLY by BaseTracker implementations (Layer 4).
    - Tracks consume Detections — they do NOT depend on the specific AI model.
    - Every Track carries camera_id — tracks from different cameras are always separate.
      Cross-camera re-identification is a future advanced capability (Milestone 17+).
    - The trajectory history supports future loitering detection, direction analysis,
      speed estimation, and suspicious behavior rules.

Future (Milestone 4+):
    - ByteTrack / BoT-SORT will produce Track updates each frame.
    - Track lifecycle management (ACTIVE → LOST → REMOVED).
    - Trajectory is the foundation for the Spatial Intelligence layer (Layer 5).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.detection import BoundingBox, ObjectClass


class TrackState(str, Enum):
    """Lifecycle state of a tracked object."""

    ACTIVE = "ACTIVE"   # Object is currently visible and being tracked
    LOST = "LOST"       # Object temporarily not visible; tracker maintaining identity
    REMOVED = "REMOVED" # Track has been terminated (object left scene or too long lost)


class TrackPoint(BaseModel):
    """
    A single position record in a Track's trajectory history.

    Attributes:
        timestamp: UTC time of this position observation.
        bounding_box: Object location at this timestamp.
        frame_id: Source frame for this observation.
    """

    timestamp: datetime = Field(..., description="UTC time of this position observation")
    bounding_box: BoundingBox = Field(..., description="Object location at this point")
    frame_id: str = Field(..., description="Source frame for this observation")


class Track(BaseModel):
    """
    Represents the persistent temporal identity of a tracked object.

    A Track aggregates multiple Detection observations across frames to build
    a coherent identity with position history. This is the primary input to
    the Spatial Intelligence layer (Layer 5) and Event Engine (Layer 6).

    Attributes:
        track_id: Tracker-assigned unique ID, persistent across frames.
            Note: track_ids are only unique within a single camera session.
        camera_id: Source camera. Tracks from different cameras are always independent.
        object_class: Class of the tracked object (from initial detection).
        bounding_box: Current position of the object (most recent update).
        trajectory: Ordered history of positions (oldest first).
            This is the foundation for loitering, direction, and speed analysis.
        first_seen: UTC time of first detection for this track.
        last_seen: UTC time of the most recent detection update.
        state: Current lifecycle state of this track.
        metadata: Extensible dictionary for tracker-specific state
            (e.g., Kalman filter state, re-ID embedding reference).

    Future:
        - speed_estimate (pixels/second or calibrated m/s)
        - direction_vector
        - re_id_embedding (for Milestone 17 cross-camera matching)
        - trajectory compression for long-duration tracks
    """

    track_id: str = Field(..., description="Tracker-assigned persistent object identifier")
    camera_id: str = Field(..., description="Source camera identifier")
    object_class: ObjectClass = Field(..., description="Class of the tracked object")
    bounding_box: BoundingBox = Field(..., description="Current position of the object")
    trajectory: list[TrackPoint] = Field(
        default_factory=list,
        description="Ordered position history (oldest first)",
    )
    first_seen: datetime = Field(..., description="UTC time of first detection")
    last_seen: datetime = Field(..., description="UTC time of most recent detection update")
    state: TrackState = Field(default=TrackState.ACTIVE)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible tracker-specific state",
    )

    @property
    def dwell_seconds(self) -> float:
        """Duration in seconds from first_seen to last_seen."""
        return (self.last_seen - self.first_seen).total_seconds()
