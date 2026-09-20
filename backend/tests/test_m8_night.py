import pytest
import numpy as np
from datetime import datetime, timedelta
from app.domain.night import SceneState
from app.domain.zone import Point
from app.night.config import NightConfig, CameraNightConfig
from app.night.scene_analyzer import SceneAnalyzer
from app.night.movement_detector import NightMovementDetector, TrackNightState

def test_scene_analyzer_hysteresis():
    # Setup
    config = NightConfig()
    config.default_config.scene_smoothing_window_frames = 3
    config.default_config.brightness_sample_interval_frames = 1
    config.default_config.low_light_enter_threshold = 45.0
    config.default_config.dark_pixel_ratio_threshold = 0.5
    
    analyzer = SceneAnalyzer(config)
    cam_id = "cam1"
    
    # 1. Day frames
    day_frame = np.full((100, 100, 3), 100, dtype=np.uint8)
    t0 = datetime.now()
    
    # Window isn't full yet, starts at DAY
    state, metrics = analyzer.analyze(cam_id, day_frame, t0)
    assert state == SceneState.DAY
    
    # 2. Start introducing night frames
    night_frame = np.full((100, 100, 3), 10, dtype=np.uint8)
    
    state, metrics = analyzer.analyze(cam_id, night_frame, t0 + timedelta(seconds=1))
    assert state == SceneState.DAY 
    
    state, metrics = analyzer.analyze(cam_id, night_frame, t0 + timedelta(seconds=2))
    assert state == SceneState.DAY 
    
    # 3. Third night frame completes the window
    state, metrics = analyzer.analyze(cam_id, night_frame, t0 + timedelta(seconds=3))
    assert state == SceneState.NIGHT 

def test_night_movement():
    config = NightConfig()
    # Speed up thresholds for test
    config.default_config.movement_smoothing_window_points = 1
    config.default_config.movement_distance_threshold_pixels = 20
    config.default_config.movement_duration_threshold_seconds = 1.0
    
    detector = NightMovementDetector(config)
    
    cam_id = "cam1"
    trk_id = "trk1"
    
    state = detector.get_or_create_state(cam_id, trk_id, "PERSON")
    
    t0 = datetime.now()
    scene = SceneState.NIGHT
    
    state.add_point(Point(x=10, y=10), t0)
    ev = detector.process_track(state, scene, t0)
    assert ev is None
    assert state.status == "MOVING"
    
    # Add point after 1.5 seconds, moved 30 pixels 
    state.add_point(Point(x=40, y=10), t0 + timedelta(seconds=1.5))
    ev = detector.process_track(state, scene, t0 + timedelta(seconds=1.5))
    
    assert ev is not None
    assert ev.event_type == "NIGHT_MOVEMENT"
    assert ev.displacement == 30.0
    assert ev.duration == 1.5
    assert state.status == "EVENT_ACTIVE"
