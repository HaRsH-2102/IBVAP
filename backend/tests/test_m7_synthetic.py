import pytest
from datetime import datetime, timedelta
from app.domain.zone import Point
from app.behavioral.config import BehavioralConfig
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.detectors import LoiteringDetector, StationaryDetector, DirectionDetector
from app.domain.behavioral import BehavioralEventType

def test_loitering_detector():
    config = BehavioralConfig(loitering_duration=5.0, loitering_radius=10.0, jitter_smoothing_window=1)
    detector = LoiteringDetector()
    state = TrackBehavioralState("cam1", "trk1")
    
    t0 = datetime.now()
    
    # Not loitering yet
    events = detector.detect(state, config, t0)
    assert len(events) == 0
    
    # Start observing
    state.add_point(Point(x=100, y=100), t0)
    detector.detect(state, config, t0)
    
    # 2 seconds later, small movement
    t1 = t0 + timedelta(seconds=2)
    state.add_point(Point(x=102, y=102), t1)
    events = detector.detect(state, config, t1)
    assert len(events) == 0 # not long enough
    
    # 6 seconds later, still small movement -> LOITERING
    t2 = t0 + timedelta(seconds=6)
    state.add_point(Point(x=105, y=105), t2)
    events = detector.detect(state, config, t2)
    assert len(events) == 1
    assert events[0].behavior_type == BehavioralEventType.LOITERING
    
    # Big movement -> NOT LOITERING
    t3 = t0 + timedelta(seconds=10)
    state.add_point(Point(x=200, y=200), t3)
    events = detector.detect(state, config, t3)
    assert len(events) == 0

def test_direction_reversal():
    config = BehavioralConfig(jitter_smoothing_window=1, direction_change_threshold_degrees=90.0)
    detector = DirectionDetector()
    state = TrackBehavioralState("cam1", "trk1")
    
    t0 = datetime.now()
    t1 = t0 + timedelta(seconds=1)
    t2 = t0 + timedelta(seconds=2)
    
    state.add_point(Point(x=100, y=100), t0)
    state.add_point(Point(x=150, y=100), t1) # Moving right
    state.add_point(Point(x=100, y=100), t2) # Reversal!
    
    events = detector.detect(state, config, t2)
    assert len(events) == 2
    assert events[0].behavior_type == BehavioralEventType.DIRECTION_REVERSAL
    assert events[1].behavior_type == BehavioralEventType.RAPID_BACKTRACK
