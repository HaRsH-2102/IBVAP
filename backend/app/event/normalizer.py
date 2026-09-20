import logging
from typing import Optional, Union
from app.domain.spatial import SpatialEvent
from app.domain.behavioral import BehavioralEvent
from app.domain.night import NightMovementEvent

logger = logging.getLogger("IBVAP.EventNormalizer")

class EventNormalizer:
    """
    Validates and normalizes incoming M5 SpatialEvents, M7 BehavioralEvents, and M8 NightMovementEvents.
    Rejects malformed events safely.
    """
    
    def normalize(self, event: Union[SpatialEvent, BehavioralEvent, NightMovementEvent]) -> Optional[Union[SpatialEvent, BehavioralEvent, NightMovementEvent]]:
        try:
            # Basic validation
            if not event.event_id:
                logger.warning(f"Rejecting event missing event_id: {event}")
                return None
            if not event.camera_id:
                logger.warning(f"Rejecting event {event.event_id} missing camera_id")
                return None
            if not event.timestamp:
                logger.warning(f"Rejecting event {event.event_id} missing timestamp")
                return None
            
            if isinstance(event, SpatialEvent):
                if not event.event_type:
                    logger.warning(f"Rejecting event {event.event_id} missing event_type")
                    return None
                if not event.spatial_object_id:
                    logger.warning(f"Rejecting event {event.event_id} missing spatial_object_id")
                    return None
                if not hasattr(event.event_type, "value"):
                    logger.warning(f"Rejecting event {event.event_id} with invalid event_type type")
                    return None
            elif isinstance(event, BehavioralEvent):
                if not event.behavior_type:
                    logger.warning(f"Rejecting event {event.event_id} missing behavior_type")
                    return None
                if not hasattr(event.behavior_type, "value"):
                    logger.warning(f"Rejecting event {event.event_id} with invalid behavior_type type")
                    return None
            elif isinstance(event, NightMovementEvent):
                if event.event_type != "NIGHT_MOVEMENT":
                    logger.warning(f"Rejecting event {event.event_id} invalid event_type for night movement")
                    return None
                
            return event
            
        except Exception as e:
            logger.error(f"Error normalizing event: {e}")
            return None
