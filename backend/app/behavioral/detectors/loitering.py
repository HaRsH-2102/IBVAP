import math
from typing import List
from datetime import datetime
from app.domain.behavioral import BehavioralEvent, BehavioralEventType
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.base import BehaviorDetector

class LoiteringDetector(BehaviorDetector):
    def detect(self, state: TrackBehavioralState, config: BehavioralConfig, timestamp: datetime) -> List[BehavioralEvent]:
        events = []
        
        # We need at least some history
        if not state.history:
            return events
            
        b_state = state.active_behaviors.setdefault(BehavioralEventType.LOITERING.value, {
            "status": "NOT_LOITERING",
            "start_time": None,
            "reference_point": None,
            "last_active_event_id": None
        })
        
        current_pt = state.get_smoothed_position(window=config.jitter_smoothing_window)
        
        if b_state["status"] == "NOT_LOITERING":
            # Start observing
            b_state["status"] = "OBSERVING"
            b_state["start_time"] = timestamp
            b_state["reference_point"] = current_pt
            
        elif b_state["status"] in ["OBSERVING", "LOITERING"]:
            # Check displacement
            ref_pt = b_state["reference_point"]
            dx = current_pt.x - ref_pt.x
            dy = current_pt.y - ref_pt.y
            dist = math.hypot(dx, dy)
            
            elapsed = (timestamp - b_state["start_time"]).total_seconds()
            
            if dist > config.loitering_radius:
                # Reset logic
                # For a true state machine, we might wait `reset_duration` before resetting.
                # For this prototype, if it moves far enough, we reset immediately.
                b_state["status"] = "NOT_LOITERING"
                b_state["start_time"] = None
                b_state["reference_point"] = None
                if b_state["last_active_event_id"]:
                    # End the behavior (handled by M6 eventually)
                    b_state["last_active_event_id"] = None
            else:
                # Still within radius
                if b_state["status"] == "OBSERVING" and elapsed >= config.loitering_duration:
                    b_state["status"] = "LOITERING"
                    
                    evidence = {
                        "duration": elapsed,
                        "movement_radius": dist,
                        "threshold_duration": config.loitering_duration,
                        "threshold_radius": config.loitering_radius
                    }
                    
                    event = self._create_event(
                        state, BehavioralEventType.LOITERING, 
                        b_state["start_time"], timestamp, elapsed, evidence
                    )
                    
                    b_state["last_active_event_id"] = event.event_id
                        
                    events.append(event)
                    
        return events
