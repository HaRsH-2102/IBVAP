import sys
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.track import Track, TrackState
from app.domain.detection import BoundingBox, ObjectClass
from app.domain.spatial import SpatialEvent, SpatialEventType
from app.domain.zone import Point
from app.behavioral.engine import BehavioralEngine
from app.behavioral.config import BehavioralConfig
from app.event.rule_engine import RuleEngine

from app.behavioral.detectors.loitering import LoiteringDetector
from app.behavioral.detectors.stationary import StationaryDetector
from app.behavioral.detectors.dwell import RestrictedZoneDwellDetector
from app.behavioral.detectors.repeated_entry import RepeatedZoneEntryDetector
from app.behavioral.detectors.direction import DirectionDetector

def test_m7_synthetic():
    print("====================================")
    print("M7 BEHAVIORAL FUNCTIONAL TEST (SYNTHETIC)")
    print("====================================")
    
    config = BehavioralConfig(
        loitering_duration=5.0,
        stationary_duration=3.0,
        restricted_zone_dwell_duration=4.0,
        repeated_zone_entry_count=3,
        repeated_zone_entry_window=60.0
    )
    
    detectors = [
        LoiteringDetector(),
        StationaryDetector(),
        RestrictedZoneDwellDetector(),
        RepeatedZoneEntryDetector(),
        DirectionDetector()
    ]
    
    behavioral_engine = BehavioralEngine(config, detectors)
    
    now = datetime.now(timezone.utc)
    
    print("\n--- Testing LOITERING & STATIONARY ---")
    track_1 = Track(
        track_id="cam1-1", camera_id="cam1", object_class=ObjectClass.PERSON, 
        bounding_box=BoundingBox(left=100.0, top=100.0, right=200.0, bottom=200.0), 
        first_seen=now, last_seen=now, state=TrackState.ACTIVE, 
        metadata={"velocity": (0.0, 0.0)}
    )
    
    for i in range(60):
        current_time = now + timedelta(seconds=i*0.1)
        track_1.last_seen = current_time
        events = behavioral_engine.process([track_1], [], current_time)
        for e in events:
            print(f"[{current_time.time()}] DETECTED: {e.behavior_type.name} on track {e.track_id}")
            
    print("\n--- Testing REPEATED_ZONE_ENTRY & RESTRICTED_ZONE_DWELL ---")
    track_2 = Track(
        track_id="cam1-2", camera_id="cam1", object_class=ObjectClass.CAR, 
        bounding_box=BoundingBox(left=300.0, top=300.0, right=400.0, bottom=400.0), 
        first_seen=now, last_seen=now, state=TrackState.ACTIVE,
        metadata={"velocity": (5.0, 5.0)}
    )
    
    for i in range(4):
        current_time = now + timedelta(seconds=i*5)
        event = SpatialEvent(
            event_id=str(uuid.uuid4()),
            event_type=SpatialEventType.ZONE_ENTER, 
            track_id="cam1-2", 
            spatial_object_id="zone_1", 
            timestamp=current_time, 
            camera_id="cam1", 
            object_class=ObjectClass.CAR,
            reference_point=Point(x=350.0, y=350.0)
        )
        events = behavioral_engine.process([track_2], [event], current_time)
        for e in events:
            print(f"[{current_time.time()}] DETECTED: {e.behavior_type.name} on track {e.track_id}")
            
    for i in range(50):
        current_time = now + timedelta(seconds=20 + i*0.1)
        track_2.last_seen = current_time
        events = behavioral_engine.process([track_2], [], current_time)
        for e in events:
            print(f"[{current_time.time()}] DETECTED: {e.behavior_type.name} on track {e.track_id}")
            
    print("\n--- Testing DIRECTION_REVERSAL & RAPID_BACKTRACK ---")
    track_3 = Track(
        track_id="cam1-3", camera_id="cam1", object_class=ObjectClass.PERSON, 
        bounding_box=BoundingBox(left=500.0, top=500.0, right=600.0, bottom=600.0), 
        first_seen=now, last_seen=now, state=TrackState.ACTIVE,
        metadata={"velocity": (10.0, 0.0)}
    )
    
    for i in range(10):
        track_3.last_seen = now + timedelta(seconds=25 + i*0.1)
        behavioral_engine.process([track_3], [], track_3.last_seen)
        
    track_3.metadata["velocity"] = (-15.0, 0.0)
    for i in range(10):
        track_3.last_seen = now + timedelta(seconds=26 + i*0.1)
        behavioral_engine.process([track_3], [], track_3.last_seen)
        
    print("\n--- Testing LOST handling and REMOVED cleanup ---")
    track_1.state = TrackState.LOST
    track_1.last_seen = now + timedelta(seconds=28)
    behavioral_engine.process([track_1], [], track_1.last_seen)
    print("Track 1 state set to LOST.")
    
    track_1.state = TrackState.REMOVED
    track_1.last_seen = now + timedelta(seconds=35)
    behavioral_engine.process([track_1], [], track_1.last_seen)
    print("Track 1 state set to REMOVED. Active track states in behavior engine:")
    print(list(behavioral_engine.track_states.keys()))

    print("\nVerification Complete.")

if __name__ == "__main__":
    test_m7_synthetic()
