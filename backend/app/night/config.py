from pydantic import BaseModel
from typing import Dict, Optional

class CameraNightConfig(BaseModel):
    low_light_enter_threshold: float = 45.0
    low_light_exit_threshold: float = 60.0
    
    scene_smoothing_window_frames: int = 15
    minimum_night_state_duration_seconds: float = 2.0
    
    movement_distance_threshold_pixels: float = 20.0
    movement_duration_threshold_seconds: float = 1.0
    movement_smoothing_window_points: int = 5
    
    brightness_sample_interval_frames: int = 5
    dark_pixel_ratio_threshold: float = 0.6
    dark_pixel_luminance_threshold: float = 30.0

class NightConfig(BaseModel):
    default_config: CameraNightConfig = CameraNightConfig()
    camera_overrides: Dict[str, CameraNightConfig] = {}
    
    def get_camera_config(self, camera_id: str) -> CameraNightConfig:
        return self.camera_overrides.get(camera_id, self.default_config)
