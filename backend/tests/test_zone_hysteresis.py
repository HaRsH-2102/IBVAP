import sys
import os
import pytest
from datetime import datetime
from shapely.geometry import Point as ShapelyPoint, Polygon, LineString

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.track import Track, TrackState
from app.domain.detection import BoundingBox, ObjectClass
from app.domain.zone import Zone, Point, ZoneType
from app.domain.virtual_line import VirtualLine, Direction
from app.domain.spatial import CameraSpatialConfig, SpatialEventType
from app.spatial.spatial_engine import SpatialEngine

def create_mock_track(track_id: str, x: float, y: float, state: TrackState = TrackState.ACTIVE) -> Track:
    # Construct a bbox where the bottom-center is (x, y)
    w = 10
    h = 20
    left = x - w/2
    right = x + w/2
    bottom = y
    top = y - h
    
    return Track(
        track_id=track_id,
        camera_id="cam_test",
        object_class=ObjectClass.CAR,
        bounding_box=BoundingBox(left=left, top=top, right=right, bottom=bottom),
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        trajectory=[],
        state=state
    )

def test_zone_hysteresis():
    engine = SpatialEngine(crossing_epsilon=3.0)
    
    zone = Zone(
        zone_id="zone1",
        camera_id="cam_test",
        name="TestZone",
        zone_type=ZoneType.RESTRICTED,
        geometry=[Point(x=100, y=100), Point(x=200, y=100), Point(x=200, y=200), Point(x=100, y=200)]
    )
    config = CameraSpatialConfig(camera_id="cam_test", zones=[zone], tripwires=[])
    
    # 1. Point clearly outside (x=50, y=150) -> dist=50 > 3.0
    tracks = [create_mock_track("t1", 50, 150)]
    events = engine.process(tracks, config)
    assert len(events) == 0
    assert engine.zone_states["t1"]["zone1"] is False
    
    # 2. Point enters 3px boundary band (x=98, y=150) -> dist=2 <= 3.0
    tracks = [create_mock_track("t1", 98, 150)]
    events = engine.process(tracks, config)
    assert len(events) == 0
    assert engine.zone_states["t1"]["zone1"] is False # Retained
    
    # 3. Point exactly on boundary (x=100, y=150) -> dist=0 <= 3.0
    tracks = [create_mock_track("t1", 100, 150)]
    events = engine.process(tracks, config)
    assert len(events) == 0
    assert engine.zone_states["t1"]["zone1"] is False # Retained
    
    # 4. Point moves clearly inside (x=150, y=150) -> dist=50 > 3.0
    tracks = [create_mock_track("t1", 150, 150)]
    events = engine.process(tracks, config)
    assert len(events) == 1
    assert events[0].event_type == SpatialEventType.ZONE_ENTER
    assert engine.zone_states["t1"]["zone1"] is True
    
    # 5. Point clearly inside again (x=160, y=150)
    tracks = [create_mock_track("t1", 160, 150)]
    events = engine.process(tracks, config)
    assert len(events) == 0
    assert engine.zone_states["t1"]["zone1"] is True
    
    # 6. Point moves into hysteresis band from inside (x=198, y=150) -> dist=2 <= 3.0
    tracks = [create_mock_track("t1", 198, 150)]
    events = engine.process(tracks, config)
    assert len(events) == 0
    assert engine.zone_states["t1"]["zone1"] is True # Retained
    
    # 7. Point jitters around boundary
    tracks = [create_mock_track("t1", 201, 150)] # dist=1 <= 3.0
    events = engine.process(tracks, config)
    assert len(events) == 0
    assert engine.zone_states["t1"]["zone1"] is True # Retained
    
    tracks = [create_mock_track("t1", 199, 150)] # dist=1 <= 3.0
    events = engine.process(tracks, config)
    assert len(events) == 0
    assert engine.zone_states["t1"]["zone1"] is True # Retained
    
    # 8. Point moves sufficiently outside (x=250, y=150) -> dist=50 > 3.0
    tracks = [create_mock_track("t1", 250, 150)]
    events = engine.process(tracks, config)
    assert len(events) == 1
    assert events[0].event_type == SpatialEventType.ZONE_EXIT
    assert engine.zone_states["t1"]["zone1"] is False
