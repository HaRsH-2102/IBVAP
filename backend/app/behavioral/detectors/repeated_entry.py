from typing import List
from datetime import datetime
from app.domain.behavioral import BehavioralEvent, BehavioralEventType
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.base import BehaviorDetector

class RepeatedZoneEntryDetector(BehaviorDetector):
    def detect(self, state: TrackBehavioralState, config: BehavioralConfig, timestamp: datetime) -> List[BehavioralEvent]:
        events = []
        
        b_state = state.active_behaviors.setdefault(BehavioralEventType.REPEATED_ZONE_ENTRY.value, {
            "last_event_time": None
        })
        
        if not state.zone_entries:
            return events
            
        # Group entries by zone
        entries_by_zone = {}
        for entry in state.zone_entries:
            entries_by_zone.setdefault(entry.zone_id, []).append(entry.timestamp)
            
        for zone_id, timestamps in entries_by_zone.items():
            # Count how many entries are within the window
            recent_entries = [t for t in timestamps if (timestamp.replace(tzinfo=None) - t.replace(tzinfo=None)).total_seconds() <= config.repeated_zone_entry_window]
            
            if len(recent_entries) >= config.repeated_zone_entry_count:
                # To prevent spamming, we only emit once per window
                last = b_state["last_event_time"]
                if not last or (timestamp - last).total_seconds() > config.repeated_zone_entry_window:
                    evidence = {
                        "zone_id": zone_id,
                        "entry_count": len(recent_entries),
                        "window_seconds": config.repeated_zone_entry_window
                    }
                    
                    # For a repeated event, start time is the first entry in the window
                    start_time = recent_entries[0]
                    duration = (timestamp - start_time).total_seconds()
                    
                    event = self._create_event(
                        state, BehavioralEventType.REPEATED_ZONE_ENTRY, 
                        start_time, timestamp, duration, evidence
                    )
                    
                    # Mark as ended since it's a discrete pattern
                    event.end_time = timestamp
                    event.spatial_context["zone_id"] = zone_id
                    
                    events.append(event)
                    b_state["last_event_time"] = timestamp
                    
        return events
