import math
from typing import List
from datetime import datetime
from app.domain.behavioral import BehavioralEvent, BehavioralEventType
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.base import BehaviorDetector

class StationaryDetector(BehaviorDetector):
    def detect(self, state: TrackBehavioralState, config: BehavioralConfig, timestamp: datetime) -> List[BehavioralEvent]:
        events = []
        
        if not state.history:
            return events
            
        b_state = state.active_behaviors.setdefault(BehavioralEventType.STATIONARY_PROLONGED.value, {
            "status": "NOT_STATIONARY",
            "start_time": None,
            "reference_point": None,
            "last_active_event_id": None
        })
        
        current_pt = state.get_smoothed_position(window=config.jitter_smoothing_window)
        
        if b_state["status"] == "NOT_STATIONARY":
            b_state["status"] = "OBSERVING"
            b_state["start_time"] = timestamp
            b_state["reference_point"] = current_pt
            
        elif b_state["status"] in ["OBSERVING", "STATIONARY"]:
            ref_pt = b_state["reference_point"]
            dx = current_pt.x - ref_pt.x
            dy = current_pt.y - ref_pt.y
            dist = math.hypot(dx, dy)
            
            elapsed = (timestamp - b_state["start_time"]).total_seconds()
            
            if dist > config.stationary_radius:
                b_state["status"] = "NOT_STATIONARY"
                b_state["start_time"] = None
                b_state["reference_point"] = None
                b_state["last_active_event_id"] = None
            else:
                if elapsed >= config.stationary_duration:
                    b_state["status"] = "STATIONARY"
                    evidence = {
                        "duration": elapsed,
                        "movement_radius": dist,
                        "threshold_duration": config.stationary_duration,
                        "threshold_radius": config.stationary_radius
                    }
                    event = self._create_event(
                        state, BehavioralEventType.STATIONARY_PROLONGED, 
                        b_state["start_time"], timestamp, elapsed, evidence
                    )
                    
                    if b_state["last_active_event_id"]:
                        event.event_id = b_state["last_active_event_id"]
                    else:
                        b_state["last_active_event_id"] = event.event_id
                        
                    events.append(event)
                    
        return events
