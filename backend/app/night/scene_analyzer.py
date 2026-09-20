import cv2
import numpy as np
import logging
from collections import deque
from datetime import datetime
from typing import Dict, Tuple

from app.domain.night import SceneState
from app.night.config import NightConfig, CameraNightConfig

logger = logging.getLogger("IBVAP.SceneAnalyzer")

class SceneAnalyzer:
    def __init__(self, config: NightConfig):
        self.config = config
        
        # State tracking per camera
        # Key: camera_id -> Dict
        self.camera_states: Dict[str, Dict] = {}
        
    def _get_or_create_state(self, camera_id: str, cam_config: CameraNightConfig, timestamp: datetime) -> Dict:
        if camera_id not in self.camera_states:
            self.camera_states[camera_id] = {
                "current_state": SceneState.DAY,
                "frame_count": 0,
                "history": deque(maxlen=cam_config.scene_smoothing_window_frames),
                "last_metrics": {},
                "state_start_time": timestamp
            }
        return self.camera_states[camera_id]

    def analyze(self, camera_id: str, frame: np.ndarray, timestamp: datetime) -> Tuple[SceneState, Dict]:
        cam_config = self.config.get_camera_config(camera_id)
        state = self._get_or_create_state(camera_id, cam_config, timestamp)
        
        state["frame_count"] += 1
        
        # Only sample periodically to save CPU
        if (state["frame_count"] - 1) % cam_config.brightness_sample_interval_frames != 0 and state["history"]:
            return state["current_state"], state["last_metrics"]
            
        try:
            # Downsample to save CPU
            h, w = frame.shape[:2]
            target_w = 320
            target_h = int(h * (target_w / w))
            small = cv2.resize(frame, (target_w, target_h))
            
            # Fast luminance calculation without color space conversion if possible, 
            # but cvtColor is fine for small res
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            
            mean_lum = float(np.mean(gray))
            median_lum = float(np.median(gray))
            
            dark_pixels = np.sum(gray < cam_config.dark_pixel_luminance_threshold)
            total_pixels = gray.size
            dark_ratio = float(dark_pixels / total_pixels)
            
            metrics = {
                "mean_luminance": mean_lum,
                "median_luminance": median_lum,
                "dark_pixel_ratio": dark_ratio
            }
            state["last_metrics"] = metrics
            
            # Determine instantaneous state
            if median_lum < cam_config.low_light_enter_threshold and dark_ratio > cam_config.dark_pixel_ratio_threshold:
                inst_state = SceneState.NIGHT
            elif median_lum < cam_config.low_light_exit_threshold:
                inst_state = SceneState.LOW_LIGHT
            else:
                inst_state = SceneState.DAY
                
            state["history"].append(inst_state)
            
            # Hysteresis: We only transition if the ENTIRE window agrees
            if len(state["history"]) == state["history"].maxlen:
                unique_states = set(state["history"])
                if len(unique_states) == 1:
                    proposed_state = unique_states.pop()
                    if proposed_state != state["current_state"]:
                        # Ensure minimum state duration before transition
                        # Wait, we want minimum duration in the CURRENT state before leaving it, 
                        # or minimum duration in NEW state?
                        # The history window acts as the minimum duration for the new state to prove itself.
                        state["current_state"] = proposed_state
                        state["state_start_time"] = timestamp
                        logger.info(f"[{camera_id}] Scene State transitioned to {proposed_state.name}")
            
            return state["current_state"], metrics
            
        except Exception as e:
            logger.error(f"Error in SceneAnalyzer for {camera_id}: {e}")
            return state["current_state"], state["last_metrics"]
