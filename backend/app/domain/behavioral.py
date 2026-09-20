from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict
from datetime import datetime

class BehavioralEventType(Enum):
    LOITERING = "LOITERING"
    STATIONARY_PROLONGED = "STATIONARY_PROLONGED"
    RESTRICTED_ZONE_DWELL = "RESTRICTED_ZONE_DWELL"
    REPEATED_ZONE_ENTRY = "REPEATED_ZONE_ENTRY"
    REPEATED_BOUNDARY_APPROACH = "REPEATED_BOUNDARY_APPROACH"
    DIRECTION_REVERSAL = "DIRECTION_REVERSAL"
    RAPID_BACKTRACK = "RAPID_BACKTRACK"

@dataclass
class BehavioralEvent:
    event_id: str
    behavior_type: BehavioralEventType
    camera_id: str
    track_id: str
    timestamp: datetime
    start_time: datetime
    end_time: Optional[datetime]
    duration: float
    spatial_context: Dict = field(default_factory=dict)
    evidence: Dict = field(default_factory=dict)
    correlation_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
