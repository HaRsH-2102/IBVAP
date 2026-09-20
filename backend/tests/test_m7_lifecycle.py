import pytest
from datetime import datetime
from app.behavioral.engine import BehavioralEngine
from app.behavioral.config import BehavioralConfig
from app.domain.spatial import SpatialEvent
from collections import namedtuple

# Mock Track object
Track = namedtuple('Track', ['camera_id', 'track_id', 'state', 'bounding_box'])
State = namedtuple('State', ['value'])
Box = namedtuple('Box', ['left', 'top', 'right', 'bottom'])

def test_track_cleanup():
    config = BehavioralConfig()
    engine = BehavioralEngine(config)
    
    t0 = datetime.now()
    
    # Send an active track
    t1 = Track("cam1", "trk1", State("ACTIVE"), Box(0, 0, 10, 10))
    engine.process([t1], [], t0)
    
    # State should exist
    assert ("cam1", "trk1") in engine.track_states
    
    # Send it as removed
    t2 = Track("cam1", "trk1", State("REMOVED"), Box(0, 0, 10, 10))
    engine.process([t2], [], t0)
    
    # State should be cleaned up
    assert ("cam1", "trk1") not in engine.track_states
