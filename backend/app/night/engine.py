import logging
from typing import List, Tuple
from datetime import datetime
import numpy as np

from app.domain.night import NightMovementEvent, SceneState
from app.domain.behavioral import BehavioralEvent
from app.night.config import NightConfig
from app.night.scene_analyzer import SceneAnalyzer
from app.night.movement_detector import NightMovementDetector
from app.domain.zone import Point

logger = logging.getLogger("IBVAP.NightEngine")

class NightEngine:
    """
    Main orchestration class for M8 Night-Time Intelligence.
    Consumes frames, tracks, and behavioral events.
    Produces NightMovementEvents and enriches BehavioralEvents.
    """
    def __init__(self, config: NightConfig = None):
        self.config = config or NightConfig()
        self.analyzer = SceneAnalyzer(self.config)
        self.movement_detector = NightMovementDetector(self.config)
        
    def process(self, camera_id: str, frame: np.ndarray, tracks: List, behavioral_events: List[BehavioralEvent], timestamp: datetime) -> Tuple[SceneState, List[NightMovementEvent]]:
        # 1. Evaluate Scene State
        scene_state, metrics = self.analyzer.analyze(camera_id, frame, timestamp)
        
        night_events = []
        
        try:
            # 2. Add trajectory points and evaluate night movement
            active_keys = set()
            for t in tracks:
                if t.state.value == "REMOVED":
                    continue
                
                active_keys.add((camera_id, t.track_id))
                track_state = self.movement_detector.get_or_create_state(camera_id, t.track_id, "UNKNOWN")
                
                # Bottom-center reference
                pt = Point(x=(t.bounding_box.left + t.bounding_box.right)/2.0, y=t.bounding_box.bottom)
                track_state.add_point(pt, timestamp)
                
                event = self.movement_detector.process_track(track_state, scene_state, timestamp)
                if event:
                    # Inject scene brightness metrics into the event
                    event.brightness_metrics = metrics
                    night_events.append(event)
                    
            # 3. Cleanup old tracks
            self.movement_detector.cleanup_removed(active_keys)
            
            # 4. Enrich behavioral events with scene state
            for b_event in behavioral_events:
                if b_event.camera_id == camera_id:
                    b_event.metadata["scene_state"] = scene_state.name
                    if metrics:
                        b_event.metadata["brightness_metrics"] = metrics
                        
        except Exception as e:
            logger.error(f"Error in NightEngine process loop for {camera_id}: {e}")
            
        return scene_state, night_events
