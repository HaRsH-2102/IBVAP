import logging
from typing import List, Dict, Tuple
from datetime import datetime

from app.domain.spatial import SpatialEvent
from app.domain.behavioral import BehavioralEvent
from app.behavioral.config import BehavioralConfig
from app.behavioral.track_state import TrackBehavioralState

logger = logging.getLogger("IBVAP.BehavioralEngine")

class BehavioralEngine:
    """
    Evaluates tracking data and spatial events over time to detect complex behaviors.
    """
    def __init__(self, config: BehavioralConfig, detectors: List = None):
        self.config = config
        # Key: (camera_id, track_id)
        self.track_states: Dict[Tuple[str, str], TrackBehavioralState] = {}
        
        self.detectors = detectors or []
        
    def _get_or_create_state(self, camera_id: str, track_id: str) -> TrackBehavioralState:
        key = (camera_id, track_id)
        if key not in self.track_states:
            self.track_states[key] = TrackBehavioralState(camera_id, track_id, max_points=self.config.max_history_points)
        return self.track_states[key]

    def _cleanup_removed_tracks(self, active_tracks: List):
        # We need a way to know which tracks are ACTIVE or LOST vs REMOVED.
        # If the input list of tracks contains only ACTIVE/LOST, we shouldn't necessarily delete the rest immediately
        # unless we have an explicit REMOVED signal.
        # For this prototype, we'll assume any track not seen in the current frame and not explicitly LOST is subject to cleanup,
        # but robust M4 implementation would explicitly mark REMOVED.
        active_keys = {(t.camera_id, t.track_id) for t in active_tracks if t.state.value != "REMOVED"}
        
        keys_to_remove = []
        for key in self.track_states.keys():
            if key not in active_keys:
                # We could add a timeout here to tolerate temporary drops (LOST state)
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.track_states[key]

    def process(self, tracks: List, spatial_events: List[SpatialEvent], timestamp: datetime) -> List[BehavioralEvent]:
        """
        Main entry point per frame.
        """
        behavioral_events = []
        
        try:
            # 1. Update Track States with spatial events
            for event in spatial_events:
                if event.track_id:
                    state = self._get_or_create_state(event.camera_id, event.track_id)
                    state.process_spatial_event(event)
                    
            # 2. Update Track States with trajectory positions
            for track in tracks:
                if track.state.value == "REMOVED":
                    continue
                state = self._get_or_create_state(track.camera_id, track.track_id)
                # Bottom-center reference point for consistency
                left, top, right, bottom = track.bounding_box.left, track.bounding_box.top, track.bounding_box.right, track.bounding_box.bottom
                from app.domain.zone import Point
                pt = Point(x=(left + right) / 2.0, y=bottom)
                state.add_point(pt, timestamp)
                
            # 3. Run Detectors
            for track in tracks:
                if track.state.value == "REMOVED":
                    continue
                state = self._get_or_create_state(track.camera_id, track.track_id)
                
                for detector in self.detectors:
                    try:
                        events = detector.detect(state, self.config, timestamp)
                        behavioral_events.extend(events)
                    except Exception as e:
                        logger.error(f"Detector {detector.__class__.__name__} failed for track {track.track_id}: {e}")
                        
            # 4. Cleanup
            self._cleanup_removed_tracks(tracks)
            
        except Exception as e:
            logger.error(f"BehavioralEngine processing error: {e}")
            
        return behavioral_events
