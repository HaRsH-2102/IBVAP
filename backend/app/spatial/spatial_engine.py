"""
IBVAP Spatial Engine
====================
Concrete implementation of the Spatial Intelligence engine using Shapely.
"""

import uuid
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from shapely.geometry import Point as ShapelyPoint, Polygon, LineString

from app.domain.track import Track, TrackState
from app.domain.spatial import SpatialEvent, SpatialEventType, CameraSpatialConfig
from app.domain.zone import Zone
from app.domain.virtual_line import VirtualLine, Direction
from app.spatial.engine_interface import BaseSpatialEngine

class SpatialEngine(BaseSpatialEngine):
    """
    Evaluates Track positions against geometric zones and tripwires.
    """
    
    def __init__(self, crossing_epsilon: float = 3.0):
        """
        Args:
            crossing_epsilon: Distance in pixels a track must move past a line
                              to confidently register a crossing state change.
        """
        self.crossing_epsilon = crossing_epsilon
        
        # State tracking dictionaries
        # Keys are track_id (str)
        # Values are Dict[zone_id, is_inside (bool)]
        self.zone_states: Dict[str, Dict[str, bool]] = {}
        
        # Keys are track_id (str)
        # Values are Dict[line_id, Tuple[last_confident_side, last_confident_point]]
        # side is 1 (Right/A) or -1 (Left/B)
        self.line_states: Dict[str, Dict[str, Tuple[int, ShapelyPoint]]] = {}

    def process(self, tracks: List[Track], config: CameraSpatialConfig) -> List[SpatialEvent]:
        events: List[SpatialEvent] = []
        current_track_ids = set()
        
        # Pre-compile geometry for performance if this was production, 
        # but for now we construct it per frame since configs could change.
        zone_polys: Dict[str, Polygon] = {
            z.zone_id: Polygon([(p.x, p.y) for p in z.geometry]) 
            for z in config.zones if z.active and z.is_valid_polygon()
        }
        
        tripwire_lines: Dict[str, LineString] = {
            l.line_id: LineString([(l.start.x, l.start.y), (l.end.x, l.end.y)])
            for l in config.tripwires if l.active
        }
        
        for track in tracks:
            current_track_ids.add(track.track_id)
            
            # We only evaluate ACTIVE tracks. LOST tracks keep their previous state.
            if track.state != TrackState.ACTIVE:
                continue
                
            # Initialize track state dicts if new
            if track.track_id not in self.zone_states:
                self.zone_states[track.track_id] = {}
            if track.track_id not in self.line_states:
                self.line_states[track.track_id] = {}
                
            # Calculate reference point: Bottom-Center
            ref_x = (track.bounding_box.left + track.bounding_box.right) / 2.0
            ref_y = track.bounding_box.bottom
            ref_point = ShapelyPoint(ref_x, ref_y)
            
            # --- ZONE EVALUATION ---
            for zone in config.zones:
                if not zone.active or zone.zone_id not in zone_polys:
                    continue
                    
                poly = zone_polys[zone.zone_id]
                
                # Check distance to boundary for hysteresis
                dist = poly.exterior.distance(ref_point)
                
                # Only evaluate state change if we are confidently inside or outside the epsilon band
                if dist > self.crossing_epsilon:
                    is_inside = poly.contains(ref_point)
                    was_inside = self.zone_states[track.track_id].get(zone.zone_id, False)
                    
                    if is_inside and not was_inside:
                        # ZONE_ENTER
                        events.append(self._create_event(
                            config.camera_id, track.track_id, SpatialEventType.ZONE_ENTER, 
                            zone.zone_id, track.last_seen, ref_x, ref_y
                        ))
                    elif not is_inside and was_inside:
                        # ZONE_EXIT
                        events.append(self._create_event(
                            config.camera_id, track.track_id, SpatialEventType.ZONE_EXIT, 
                            zone.zone_id, track.last_seen, ref_x, ref_y
                        ))
                        
                    self.zone_states[track.track_id][zone.zone_id] = is_inside
                
            # --- TRIPWIRE EVALUATION ---
            for line_config in config.tripwires:
                if not line_config.active:
                    continue
                    
                line_id = line_config.line_id
                line_geom = tripwire_lines[line_id]
                
                # We calculate signed distance (cross product) to the infinite line
                # P1 -> P2
                p1_x, p1_y = line_config.start.x, line_config.start.y
                p2_x, p2_y = line_config.end.x, line_config.end.y
                
                # Cross product to determine side
                # Vector AB = (p2_x - p1_x, p2_y - p1_y)
                # Vector AP = (ref_x - p1_x, ref_y - p1_y)
                cross = (p2_x - p1_x) * (ref_y - p1_y) - (p2_y - p1_y) * (ref_x - p1_x)
                
                # Side A = 1 (cross > 0), Side B = -1 (cross < 0)
                current_side = 1 if cross >= 0 else -1
                
                # Calculate absolute distance to the infinite line segment
                dist = line_geom.distance(ref_point)
                
                # Hysteresis check
                if dist > self.crossing_epsilon:
                    # We are confidently on `current_side`
                    
                    if line_id in self.line_states[track.track_id]:
                        last_side, last_point = self.line_states[track.track_id][line_id]
                        
                        if last_side != current_side:
                            # We swapped sides confidently! Check if we actually crossed the segment.
                            track_segment = LineString([last_point, ref_point])
                            if track_segment.intersects(line_geom):
                                # Valid crossing! Check direction allowed.
                                direction = Direction.A_TO_B if last_side == 1 else Direction.B_TO_A
                                
                                if line_config.allowed_direction in [Direction.BOTH, direction]:
                                    # Create Event
                                    events.append(self._create_event(
                                        config.camera_id, track.track_id, SpatialEventType.LINE_CROSS,
                                        line_id, track.last_seen, ref_x, ref_y,
                                        metadata={"direction": direction.value}
                                    ))
                                    
                            # Update confident side and point
                            self.line_states[track.track_id][line_id] = (current_side, ref_point)
                    else:
                        # First time we establish a confident side
                        self.line_states[track.track_id][line_id] = (current_side, ref_point)
                        
        # --- STATE CLEANUP ---
        # If a track_id is in our state but not in the current_track_ids, it means it was REMOVED
        removed_ids = set(self.zone_states.keys()) - current_track_ids
        for r_id in removed_ids:
            del self.zone_states[r_id]
            if r_id in self.line_states:
                del self.line_states[r_id]
                
        # Sort events deterministically: timestamp -> track_id -> spatial_object_id
        events.sort(key=lambda e: (e.timestamp, e.track_id, e.spatial_object_id))
                
        return events

    def _create_event(self, cam_id: str, track_id: str, event_type: SpatialEventType, 
                      obj_id: str, ts: datetime, x: float, y: float, 
                      metadata: Optional[Dict] = None) -> SpatialEvent:
        from app.domain.zone import Point
        return SpatialEvent(
            event_id=str(uuid.uuid4()),
            camera_id=cam_id,
            track_id=track_id,
            event_type=event_type,
            spatial_object_id=obj_id,
            timestamp=ts,
            reference_point=Point(x=x, y=y),
            metadata=metadata or {}
        )
