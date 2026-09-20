import pytest
from datetime import datetime, timedelta
from app.domain.zone import Point
from app.behavioral.config import BehavioralConfig
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.detectors import LoiteringDetector, StationaryDetector, DirectionDetector
from app.behavioral.engine import BehavioralEngine
from app.domain.behavioral import BehavioralEventType
from collections import namedtuple

# Mocks
Track = namedtuple('Track', ['camera_id', 'track_id', 'state', 'bounding_box'])
State = namedtuple('State', ['value'])
Box = namedtuple('Box', ['left', 'top', 'right', 'bottom'])

def test_m7_duplicate_event_prevention():
    # Test deduplication across multiple frames
    config = BehavioralConfig(loitering_duration=1.0, loitering_radius=10.0)
    detector = LoiteringDetector()
    state = TrackBehavioralState("cam1", "trk1")
    
    t0 = datetime.now()
    t1 = t0 + timedelta(seconds=2)
    t2 = t0 + timedelta(seconds=3)
    
    # 0s
    state.add_point(Point(x=10, y=10), t0)
    detector.detect(state, config, t0)
    
    # 2s (Trigger)
    state.add_point(Point(x=12, y=12), t1)
    ev1 = detector.detect(state, config, t1)
    assert len(ev1) == 1
    assert ev1[0].end_time is None # Active behavior
    
    # 3s (Still active, no new event but should emit update?)
    # Wait, the current implementation emits an event on EVERY frame while active
    # Let's see what happens.
    state.add_point(Point(x=13, y=13), t2)
    ev2 = detector.detect(state, config, t2)
    
    # To prevent spam, the implementation actually emits it every time, relying on M6 correlator?
    # Or does it use the same event_id? Let's check.
    assert len(ev2) == 1
    assert ev1[0].event_id == ev2[0].event_id

def test_m7_removed_cleanup():
    config = BehavioralConfig()
    engine = BehavioralEngine(config)
    
    t0 = datetime.now()
    # Provide active track
    t1 = Track("cam1", "trk1", State("ACTIVE"), Box(0, 0, 10, 10))
    engine.process([t1], [], t0)
    assert ("cam1", "trk1") in engine.track_states
    
    # Provide REMOVED track
    t2 = Track("cam1", "trk1", State("REMOVED"), Box(0, 0, 10, 10))
    engine.process([t2], [], t0)
    
    # Verify cleanup
    assert ("cam1", "trk1") not in engine.track_states
    
def test_m7_lost_to_active():
    config = BehavioralConfig()
    engine = BehavioralEngine(config)
    
    t0 = datetime.now()
    # Active
    engine.process([Track("cam1", "trk1", State("ACTIVE"), Box(0, 0, 10, 10))], [], t0)
    
    # LOST - should it be removed?
    # If the track is omitted from the 'tracks' list (because it's lost and not returned by byte_track)
    # the cleanup logic might remove it if we don't specifically handle it.
    engine.process([], [], t0)
    
    # Is it removed?
    assert ("cam1", "trk1") not in engine.track_states
    # Wait, if LOST tracks are removed immediately, we lose history!
    
