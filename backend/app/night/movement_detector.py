import uuid
import math
import logging
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from app.domain.night import NightMovementEvent, SceneState
from app.night.config import NightConfig, CameraNightConfig
from app.domain.zone import Point

logger = logging.getLogger("IBVAP.NightMovementDetector")

class TrackNightState:
    def __init__(self, camera_id: str, track_id: str, object_class: str, max_points: int = 30):
        self.camera_id = camera_id
        self.track_id = track_id
        self.object_class = object_class
        
        self.history = deque(maxlen=max_points)
        
        # State machine
        # NOT_MOVING -> MOVING -> EVENT_ACTIVE -> ENDED
        self.status = "NOT_MOVING"
        self.movement_start_time: Optional[datetime] = None
        self.reference_point: Optional[Point] = None
        self.last_active_event_id: Optional[str] = None
        
    def add_point(self, pt: Point, timestamp: datetime):
        self.history.append((pt, timestamp))
        
    def get_smoothed_position(self, window: int) -> Optional[Point]:
        if not self.history:
            return None
        recent = list(self.history)[-window:]
        avg_x = sum(p[0].x for p in recent) / len(recent)
        avg_y = sum(p[0].y for p in recent) / len(recent)
        return Point(x=avg_x, y=avg_y)

class NightMovementDetector:
    def __init__(self, config: NightConfig):
        self.config = config
        
        # Key: (camera_id, track_id)
        self.track_states: Dict[Tuple[str, str], TrackNightState] = {}
        
    def get_or_create_state(self, camera_id: str, track_id: str, object_class: str) -> TrackNightState:
        key = (camera_id, track_id)
        if key not in self.track_states:
            self.track_states[key] = TrackNightState(
                camera_id, 
                track_id, 
                object_class,
                max_points=30
            )
        return self.track_states[key]
        
    def cleanup_removed(self, active_keys: set):
        keys_to_remove = [k for k in self.track_states if k not in active_keys]
        for k in keys_to_remove:
            del self.track_states[k]
            
    def process_track(self, state: TrackNightState, scene_state: SceneState, timestamp: datetime) -> Optional[NightMovementEvent]:
        # Only evaluate movement if scene is NIGHT
        if scene_state != SceneState.NIGHT:
            # If we were tracking movement, reset it because it's no longer night
            if state.status != "NOT_MOVING":
                state.status = "NOT_MOVING"
                state.movement_start_time = None
                state.reference_point = None
                state.last_active_event_id = None
            return None
            
        cam_config = self.config.get_camera_config(state.camera_id)
        
        current_pt = state.get_smoothed_position(window=cam_config.movement_smoothing_window_points)
        if not current_pt:
            return None
            
        if state.status == "NOT_MOVING":
            state.status = "MOVING"
            state.movement_start_time = timestamp
            state.reference_point = current_pt
            return None
            
        elif state.status in ["MOVING", "EVENT_ACTIVE"]:
            ref_pt = state.reference_point
            dx = current_pt.x - ref_pt.x
            dy = current_pt.y - ref_pt.y
            dist = math.hypot(dx, dy)
            
            elapsed = (timestamp - state.movement_start_time).total_seconds()
            
            # If the object hasn't moved beyond threshold in the required time, we could reset it.
            # But the M8 spec says a continuous movement episode is one occurrence.
            # We'll trigger when the distance crosses threshold AND duration crosses threshold.
            if dist >= cam_config.movement_distance_threshold_pixels and elapsed >= cam_config.movement_duration_threshold_seconds:
                state.status = "EVENT_ACTIVE"
                
                event_id = state.last_active_event_id or f"nmvt-{uuid.uuid4().hex[:8]}"
                state.last_active_event_id = event_id
                
                evidence = {
                    "displacement_px": dist,
                    "duration_sec": elapsed
                }
                
                return NightMovementEvent(
                    event_id=event_id,
                    camera_id=state.camera_id,
                    track_id=state.track_id,
                    object_class=state.object_class,
                    timestamp=timestamp,
                    start_time=state.movement_start_time,
                    end_time=None,
                    duration=elapsed,
                    displacement=dist,
                    scene_state=scene_state,
                    evidence=evidence
                )
                
        return None
