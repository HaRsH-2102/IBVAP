from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict
from datetime import datetime

class SceneState(Enum):
    DAY = "DAY"
    LOW_LIGHT = "LOW_LIGHT"
    NIGHT = "NIGHT"

@dataclass
class NightMovementEvent:
    event_id: str
    camera_id: str
    track_id: str
    object_class: str
    timestamp: datetime
    start_time: datetime
    end_time: Optional[datetime]
    duration: float
    displacement: float
    scene_state: SceneState
    brightness_metrics: Dict = field(default_factory=dict)
    spatial_context: Dict = field(default_factory=dict)
    evidence: Dict = field(default_factory=dict)
    correlation_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return "NIGHT_MOVEMENT"
