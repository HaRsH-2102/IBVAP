from typing import List
from datetime import datetime
from app.domain.behavioral import BehavioralEvent, BehavioralEventType
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.base import BehaviorDetector

class BoundaryApproachDetector(BehaviorDetector):
    def detect(self, state: TrackBehavioralState, config: BehavioralConfig, timestamp: datetime) -> List[BehavioralEvent]:
        events = []
        
        b_state = state.active_behaviors.setdefault(BehavioralEventType.REPEATED_BOUNDARY_APPROACH.value, {
            "last_event_time": None
        })
        
        if not state.boundary_approaches:
            return events
            
        approaches_by_line = {}
        for approach in state.boundary_approaches:
            approaches_by_line.setdefault(approach.line_id, []).append(approach.timestamp)
            
        for line_id, timestamps in approaches_by_line.items():
            recent_approaches = [t for t in timestamps if (timestamp.replace(tzinfo=None) - t.replace(tzinfo=None)).total_seconds() <= config.boundary_approach_window]
            
            if len(recent_approaches) >= config.boundary_approach_count:
                last = b_state["last_event_time"]
                if not last or (timestamp - last).total_seconds() > config.boundary_approach_window:
                    evidence = {
                        "line_id": line_id,
                        "approach_count": len(recent_approaches),
                        "window_seconds": config.boundary_approach_window
                    }
                    
                    start_time = recent_approaches[0]
                    duration = (timestamp - start_time).total_seconds()
                    
                    event = self._create_event(
                        state, BehavioralEventType.REPEATED_BOUNDARY_APPROACH, 
                        start_time, timestamp, duration, evidence
                    )
                    
                    event.end_time = timestamp
                    event.spatial_context["line_id"] = line_id
                    
                    events.append(event)
                    b_state["last_event_time"] = timestamp
                    
        return events
