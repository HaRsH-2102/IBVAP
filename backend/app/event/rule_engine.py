import uuid
import logging
from typing import List, Dict, Optional, Union
from datetime import datetime

from app.domain.spatial import SpatialEvent
from app.domain.behavioral import BehavioralEvent
from app.domain.night import NightMovementEvent
from app.domain.rule import Rule
from app.domain.security import SecurityEvent

logger = logging.getLogger("IBVAP.RuleEngine")

class RuleEngine:
    """
    Evaluates SpatialEvents and BehavioralEvents against configured Rules to produce SecurityEvents.
    """
    def __init__(self, rules: List[Rule]):
        self.rules = [r for r in rules if r.enabled]
        # Sort deterministically by priority (higher first), then rule_id for tie-breaker
        self.rules.sort(key=lambda r: (r.priority, r.rule_id), reverse=True)
        
    def _matches_scope(self, scope: Optional[List[str]], value: str) -> bool:
        if scope is None or len(scope) == 0:
            return True
        if "ALL" in scope:
            return True
        return value in scope

    def evaluate(self, event: Union[SpatialEvent, BehavioralEvent, NightMovementEvent]) -> List[SecurityEvent]:
        security_events = []
        
        is_behavioral = isinstance(event, BehavioralEvent)
        is_night = isinstance(event, NightMovementEvent)
        
        if is_behavioral:
            event_type_val = event.behavior_type.value
        elif is_night:
            event_type_val = event.event_type
        else:
            event_type_val = event.event_type.value
        
        # Spatial object ID mapping
        spatial_obj_id = "UNKNOWN"
        if is_behavioral:
            spatial_obj_id = event.spatial_context.get("zone_id") or event.spatial_context.get("line_id") or "UNKNOWN"
        elif is_night:
            spatial_obj_id = event.spatial_context.get("zone_id") or event.spatial_context.get("line_id") or "UNKNOWN"
        else:
            spatial_obj_id = event.spatial_object_id
        
        for rule in self.rules:
            try:
                # 1. Event Type Match
                if not self._matches_scope(rule.event_type, event_type_val):
                    continue
                    
                # 2. Camera Match
                if not self._matches_scope(rule.camera_scope, event.camera_id):
                    continue
                    
                # 3. Spatial Object Match
                if not self._matches_scope(rule.spatial_object_scope, spatial_obj_id):
                    continue
                    
                # 4. Direction Match (if applicable)
                if rule.direction_scope and "ALL" not in rule.direction_scope:
                    event_direction = event.metadata.get("direction")
                    if not event_direction or not self._matches_scope(rule.direction_scope, event_direction):
                        continue
                        
                # 5. Object Class Match (if applicable)
                event_class = event.metadata.get("object_class", "UNKNOWN")
                if rule.object_class_scope and "ALL" not in rule.object_class_scope:
                    if event_class == "UNKNOWN":
                        continue
                    if not self._matches_scope(rule.object_class_scope, event_class):
                        continue
                        
                # Match found! Create SecurityEvent
                sec_event = SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=rule.security_event_type,
                    severity=rule.severity,
                    camera_id=event.camera_id,
                    track_id=event.track_id,
                    source_spatial_event_id=event.event_id, # Can refer to behavioral event ID as well
                    rule_id=rule.rule_id,
                    timestamp=event.timestamp,
                    description=rule.description if rule.description else f"Rule '{rule.name}' matched {event_type_val} on {spatial_obj_id}",
                    metadata={
                        "is_behavioral": is_behavioral
                    }
                )
                
                # Copy evidence if behavioral or anpr
                if is_behavioral:
                    sec_event.metadata["evidence"] = event.evidence
                elif not is_night:
                    sec_event.metadata["spatial_event"] = {
                        "reference_point": {"x": event.reference_point.x, "y": event.reference_point.y}
                    }
                    
                security_events.append(sec_event)
                
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id} for event {event.event_id}: {e}")
                
        return security_events
