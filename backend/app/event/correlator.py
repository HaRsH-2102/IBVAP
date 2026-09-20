import uuid
import logging
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from app.domain.security import SecurityEvent
from app.domain.rule import Rule

logger = logging.getLogger("IBVAP.BasicCorrelator")

class BasicCorrelator:
    """
    Performs basic temporal correlation of SecurityEvents within a configurable window.
    Groups events by (camera_id, track_id) to prevent alert spam for rapid sequences.
    """
    def __init__(self, rules: List[Rule]):
        self.rules = {r.rule_id: r for r in rules}
        
        # State tracking for active correlations
        # Key: (camera_id, track_id)
        # Value: Dict {"start_time": datetime, "correlation_id": str, "events": list}
        self.active_contexts: Dict[tuple, Dict] = {}
        
    def _cleanup_expired_contexts(self, current_time: datetime):
        """Removes contexts that have exceeded their maximum window."""
        expired_keys = []
        for key, context in self.active_contexts.items():
            # Get the max window from the rules of the events in this context
            max_window = 0
            for rule_id in context["rule_ids"]:
                rule = self.rules.get(rule_id)
                if rule and rule.correlation_policy and rule.correlation_policy.enabled:
                    max_window = max(max_window, rule.correlation_policy.window_seconds)
            
            if max_window == 0:
                max_window = 5 # fallback default
                
            if current_time.replace(tzinfo=None) - context["start_time"].replace(tzinfo=None) > timedelta(seconds=max_window):
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.active_contexts[key]

    def correlate(self, events: List[SecurityEvent]) -> List[SecurityEvent]:
        correlated_events = []
        
        for event in events:
            try:
                rule = self.rules.get(event.rule_id)
                if not rule or not rule.correlation_policy or not rule.correlation_policy.enabled:
                    # Pass through without correlation
                    correlated_events.append(event)
                    continue
                
                # Cleanup expired contexts relative to THIS event's timestamp
                self._cleanup_expired_contexts(event.timestamp)
                
                # Determine grouping key (configurable via rule, defaulting to camera + track)
                key_parts = []
                for context_field in rule.correlation_policy.matching_context:
                    if context_field == "camera_id":
                        key_parts.append(event.camera_id)
                    elif context_field == "track_id":
                        key_parts.append(event.track_id)
                    elif context_field == "rule_id":
                        key_parts.append(event.rule_id)
                        
                # Only correlate if we have a valid key (e.g., track_id is present)
                if not key_parts or any(p is None for p in key_parts):
                    correlated_events.append(event)
                    continue
                    
                key = tuple(key_parts)
                
                if key in self.active_contexts:
                    # Add to existing context
                    context = self.active_contexts[key]
                    event.correlation_id = context["correlation_id"]
                    context["rule_ids"].add(event.rule_id)
                else:
                    # Start new context
                    correlation_id = f"corr-{uuid.uuid4().hex[:8]}"
                    event.correlation_id = correlation_id
                    self.active_contexts[key] = {
                        "start_time": event.timestamp,
                        "correlation_id": correlation_id,
                        "rule_ids": {event.rule_id}
                    }
                
                correlated_events.append(event)
                
            except Exception as e:
                logger.error(f"Error correlating event {event.event_id}: {e}")
                correlated_events.append(event) # Fallback to pass-through
                
        return correlated_events
