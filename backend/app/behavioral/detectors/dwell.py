from typing import List
from datetime import datetime
from app.domain.behavioral import BehavioralEvent, BehavioralEventType
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.base import BehaviorDetector

class RestrictedZoneDwellDetector(BehaviorDetector):
    def detect(self, state: TrackBehavioralState, config: BehavioralConfig, timestamp: datetime) -> List[BehavioralEvent]:
        events = []
        
        b_state = state.active_behaviors.setdefault(BehavioralEventType.RESTRICTED_ZONE_DWELL.value, {
            "active_zones": {} # zone_id -> {"start_time": ts, "last_active_event_id": str}
        })
        
        # Cleanup zones we are no longer in
        zones_to_remove = []
        for z in b_state["active_zones"].keys():
            if z not in state.active_zones:
                zones_to_remove.append(z)
                
        for z in zones_to_remove:
            del b_state["active_zones"][z]
            
        # Check active zones
        for zone_id in state.active_zones:
            if zone_id not in b_state["active_zones"]:
                b_state["active_zones"][zone_id] = {
                    "start_time": timestamp,
                    "last_active_event_id": None
                }
                continue
                
            zone_state = b_state["active_zones"][zone_id]
            elapsed = (timestamp - zone_state["start_time"]).total_seconds()
            
            if elapsed >= config.restricted_zone_dwell_duration:
                evidence = {
                    "zone_id": zone_id,
                    "duration": elapsed,
                    "threshold_duration": config.restricted_zone_dwell_duration
                }
                event = self._create_event(
                    state, BehavioralEventType.RESTRICTED_ZONE_DWELL, 
                    zone_state["start_time"], timestamp, elapsed, evidence
                )
                
                # Add spatial context so M6 can filter on zone
                event.spatial_context["zone_id"] = zone_id
                
                if zone_state["last_active_event_id"]:
                    event.event_id = zone_state["last_active_event_id"]
                else:
                    zone_state["last_active_event_id"] = event.event_id
                    
                events.append(event)
                
        return events
