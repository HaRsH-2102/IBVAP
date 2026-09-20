import uuid
import logging
from typing import List, Dict, Optional
from datetime import datetime

from app.domain.security import SecurityEvent, Alert, AlertStatus

logger = logging.getLogger("IBVAP.AlertManager")

class AlertManager:
    """
    Manages the lifecycle and deduplication of Alerts based on SecurityEvents.
    Provides the abstract boundary to the persistent repository.
    """
    def __init__(self, repository):
        """
        repository: an abstraction that implements get_open_alert_by_dedup_key, save_alert, etc.
        """
        self.repository = repository
        
    def _generate_dedup_key(self, event: SecurityEvent, spatial_object_id: str) -> str:
        """
        Generates the deduplication key defined by M6:
        camera_id + track_id + rule_id + spatial_object_id
        """
        return f"{event.camera_id}:{event.track_id}:{event.rule_id}:{spatial_object_id}"

    def process_events(self, events: List[SecurityEvent]) -> List[Alert]:
        alerts_generated = []
        
        for event in events:
            try:
                spatial_object_id = event.metadata.get("spatial_event", {}).get("spatial_object_id", "UNKNOWN")
                dedup_key = self._generate_dedup_key(event, spatial_object_id)
                
                # Check for an existing OPEN or ACKNOWLEDGED alert for this condition
                existing_alert = self.repository.get_active_alert_by_dedup_key(dedup_key)
                
                if existing_alert:
                    # Deduplication case: The active condition persists.
                    # We just update the updated_at timestamp and maybe append the event_id
                    existing_alert.updated_at = event.timestamp
                    if event.event_id not in existing_alert.security_event_ids:
                        existing_alert.security_event_ids.append(event.event_id)
                    self.repository.save_alert(existing_alert)
                    # We don't consider this a NEW alert for generation metrics, but it is updated
                else:
                    # New alert needed
                    new_alert = Alert(
                        alert_id=str(uuid.uuid4()),
                        security_event_ids=[event.event_id],
                        camera_id=event.camera_id,
                        track_id=event.track_id,
                        rule_id=event.rule_id,
                        spatial_object_id=spatial_object_id,
                        event_type=event.event_type,
                        severity=event.severity,
                        created_at=event.timestamp,
                        updated_at=event.timestamp,
                        status=AlertStatus.OPEN,
                        title=f"{event.severity.value} Alert: {event.event_type}",
                        description=event.description,
                        correlation_id=event.correlation_id,
                        metadata={"dedup_key": dedup_key}
                    )
                    self.repository.save_alert(new_alert)
                    alerts_generated.append(new_alert)
                    
            except Exception as e:
                logger.error(f"Error managing alert for event {event.event_id}: {e}")
                
        return alerts_generated
