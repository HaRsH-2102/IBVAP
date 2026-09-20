from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set
from collections import deque
from datetime import datetime

from app.domain.spatial import SpatialEvent, SpatialEventType
from app.domain.zone import Point

@dataclass
class TrajectoryPoint:
    timestamp: datetime
    point: Point
    
@dataclass
class ZoneEntry:
    zone_id: str
    timestamp: datetime

@dataclass
class BoundaryApproach:
    line_id: str
    timestamp: datetime

class TrackBehavioralState:
    """
    Maintains bounded temporal state for a single tracked object (camera_id + track_id).
    This acts as the memory for behavioral detectors.
    """
    def __init__(self, camera_id: str, track_id: str, max_points: int = 300):
        self.camera_id = camera_id
        self.track_id = track_id
        
        # Bounded trajectory history
        self.history = deque(maxlen=max_points)
        
        # Zone occupancy tracking
        self.active_zones: Set[str] = set()
        self.zone_entries: List[ZoneEntry] = []
        
        # Boundary approaches (approaches without crossing)
        # Note: True approach detection would require computing distance to the line over time.
        # For M7 prototype, we will just track when the detector flags an approach.
        self.boundary_approaches: List[BoundaryApproach] = []
        
        # Active behavioral events (keyed by behavior type)
        self.active_behaviors: Dict[str, dict] = {}
        
    def add_point(self, pt: Point, timestamp: datetime):
        self.history.append(TrajectoryPoint(timestamp, pt))
        
    def process_spatial_event(self, event: SpatialEvent):
        """Update internal occupancy and approach counters based on M5 spatial events."""
        if event.event_type == SpatialEventType.ZONE_ENTER:
            self.active_zones.add(event.spatial_object_id)
            self.zone_entries.append(ZoneEntry(event.spatial_object_id, event.timestamp))
            # Cleanup old entries (e.g. keep last 10)
            if len(self.zone_entries) > 20:
                self.zone_entries.pop(0)
                
        elif event.event_type == SpatialEventType.ZONE_EXIT:
            self.active_zones.discard(event.spatial_object_id)
            
        elif event.event_type == SpatialEventType.LINE_CROSS:
            # We crossed it. We could reset approaches here, but let's just log it.
            pass
            
    def get_smoothed_position(self, window: int = 5) -> Point:
        """Returns the average position over the last N points to reduce jitter."""
        if not self.history:
            return Point(x=0.0, y=0.0)
            
        pts = list(self.history)[-window:]
        avg_x = sum(p.point.x for p in pts) / len(pts)
        avg_y = sum(p.point.y for p in pts) / len(pts)
        return Point(x=avg_x, y=avg_y)
