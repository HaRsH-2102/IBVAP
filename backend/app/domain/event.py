"""
IBVAP Domain — Event
=====================
Represents a meaningful security observation detected by the surveillance system.

An Event is the core output of the IBVAP intelligence pipeline. It is the
boundary between raw AI perception/tracking data and actionable security intelligence.

Architectural note:
    - Events are produced by the EventEngine (Layer 6) from spatial observations,
      temporal state, and track data. They are NEVER produced directly by AI models.
    - An Event's severity may be updated by the RiskEngine (Layer 7).
    - Significant Events generate Alerts (operator-facing notifications).
    - Events eventually generate Evidence associations (Milestone 13).
    - Events are the primary unit of historical audit and review.

Future (Milestone 6+):
    - EventEngine implementations for each event type
    - Compound events (correlated from multiple observations)
    - Event deduplication/suppression logic
    - Event correlation with prior events from same track
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.severity import SeverityLevel


class EventType(str, Enum):
    """
    Classification of security events detectable by IBVAP.

    Each type corresponds to a specific EventEngine rule implementation (future).
    """

    INTRUSION = "INTRUSION"                     # Object entered a restricted zone
    LOITERING = "LOITERING"                     # Object remained in area beyond threshold
    LINE_CROSSING = "LINE_CROSSING"             # Object crossed a virtual line
    WRONG_DIRECTION = "WRONG_DIRECTION"         # Object crossed line in prohibited direction
    NIGHT_MOVEMENT = "NIGHT_MOVEMENT"           # Movement detected during night hours
    VEHICLE_INTRUSION = "VEHICLE_INTRUSION"     # Vehicle entered restricted zone
    ANPR_DETECTION = "ANPR_DETECTION"           # License plate recognized (Milestone 8)
    FACE_DETECTION = "FACE_DETECTION"           # Face detected (Milestone 9)
    ZONE_ENTRY = "ZONE_ENTRY"                   # Object entered a monitored zone
    ZONE_EXIT = "ZONE_EXIT"                     # Object exited a monitored zone
    COMPOUND = "COMPOUND"                       # Multiple correlated observations
    UNKNOWN = "UNKNOWN"                         # Catch-all for unclassified events


class EventStatus(str, Enum):
    """Lifecycle status of an event."""

    OPEN = "OPEN"               # Event detected, not yet processed
    ACKNOWLEDGED = "ACKNOWLEDGED"  # Operator has seen this event
    CLOSED = "CLOSED"           # Event resolved or no longer relevant
    SUPPRESSED = "SUPPRESSED"   # Event suppressed by system rules (dedup, etc.)


class Event(BaseModel):
    """
    Represents a meaningful security observation.

    Events are the output of the EventEngine (Layer 6). They represent
    security-relevant conclusions drawn from tracking + spatial analysis.

    An Event must have a machine-readable reason — it should always be
    possible to explain why an event was generated (Rule 8).

    Attributes:
        event_id: Unique identifier.
        camera_id: Source camera. Full lineage maintained.
        event_type: Classification of the security observation.
        track_id: The tracked object that caused this event (if applicable).
        zone_id: Zone involved in this event (for zone-based events).
        line_id: Virtual line involved in this event (for crossing events).
        timestamp: UTC time when the event condition was first detected.
        confidence: Confidence score for this event [0.0, 1.0].
        severity: Initial severity (may be updated by RiskEngine).
        status: Current lifecycle status.
        evidence_ids: IDs of associated Evidence objects (populated by EvidenceManager).
        metadata: Extensible event-specific details:
            - dwell_seconds: for LOITERING events
            - plate_text: for ANPR_DETECTION events
            - crossing_direction: for LINE_CROSSING events
            - time_context: "NIGHT" or "DAY" for NIGHT_MOVEMENT events

    Future:
        - Compound event references (correlated_event_ids)
        - Operator notes on event
        - Escalation chain
    """

    event_id: str = Field(..., description="Unique event identifier (UUID)")
    camera_id: str = Field(..., description="Source camera identifier")
    event_type: EventType = Field(..., description="Classification of the security observation")
    track_id: str | None = Field(default=None, description="Tracked object that caused this event")
    zone_id: str | None = Field(default=None, description="Zone involved in this event")
    line_id: str | None = Field(default=None, description="Virtual line involved in this event")
    timestamp: datetime = Field(..., description="UTC time of event detection")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Event confidence [0.0, 1.0]")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM)
    status: EventStatus = Field(default=EventStatus.OPEN)
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="IDs of associated Evidence objects",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific details (dwell_seconds, plate_text, direction, etc.)",
    )
