import uuid
from typing import List
from datetime import datetime
from app.domain.behavioral import BehavioralEvent, BehavioralEventType
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.config import BehavioralConfig

class BehaviorDetector:
    def detect(self, state: TrackBehavioralState, config: BehavioralConfig, timestamp: datetime) -> List[BehavioralEvent]:
        raise NotImplementedError

    def _create_event(self, state: TrackBehavioralState, behavior_type: BehavioralEventType, 
                      start_time: datetime, timestamp: datetime, duration: float, evidence: dict) -> BehavioralEvent:
        return BehavioralEvent(
            event_id=str(uuid.uuid4()),
            behavior_type=behavior_type,
            camera_id=state.camera_id,
            track_id=state.track_id,
            timestamp=timestamp,
            start_time=start_time,
            end_time=None, # Active
            duration=duration,
            evidence=evidence
        )
