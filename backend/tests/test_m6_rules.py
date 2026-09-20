import sys
import os
import pytest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.spatial import SpatialEvent, SpatialEventType
from app.domain.zone import Point
from app.domain.rule import Rule, Severity
from app.event.rule_engine import RuleEngine

def create_mock_event(event_type=SpatialEventType.ZONE_ENTER, 
                      cam="cam_01", track="t1", obj="zone_01",
                      obj_class="UNKNOWN"):
    return SpatialEvent(
        event_id="evt_01",
        camera_id=cam,
        track_id=track,
        event_type=event_type,
        spatial_object_id=obj,
        timestamp=datetime.utcnow(),
        reference_point=Point(x=10, y=10),
        metadata={"object_class": obj_class}
    )

def test_rule_matching():
    # Rule expecting a car
    rule_car = Rule(
        rule_id="r1", name="Car Entry", security_event_type="VEHICLE_INTRUSION",
        severity=Severity.HIGH, event_type=["ZONE_ENTER"], object_class_scope=["car"]
    )
    
    # Rule expecting anything
    rule_any = Rule(
        rule_id="r2", name="Any Entry", security_event_type="ZONE_INTRUSION",
        severity=Severity.LOW, event_type=["ZONE_ENTER"]
    )
    
    engine = RuleEngine([rule_car, rule_any])
    
    # Test 1: UNKNOWN class event
    evt_unknown = create_mock_event(obj_class="UNKNOWN")
    res = engine.evaluate(evt_unknown)
    
    # Should only match rule_any, because rule_car explicitly wants 'car', and 'UNKNOWN' must not falsely match
    assert len(res) == 1
    assert res[0].rule_id == "r2"
    
    # Test 2: 'car' class event
    evt_car = create_mock_event(obj_class="car")
    res = engine.evaluate(evt_car)
    
    # Should match both rules
    assert len(res) == 2
    rule_ids = [r.rule_id for r in res]
    assert "r1" in rule_ids
    assert "r2" in rule_ids

def test_rule_exclusivity():
    # If multiple rules match, both emit events unless they are filtered by some exclusive manager.
    # M6 spec says they legitimately both emit events.
    r1 = Rule(rule_id="r1", name="A", security_event_type="A", severity=Severity.LOW)
    r2 = Rule(rule_id="r2", name="B", security_event_type="B", severity=Severity.HIGH)
    
    engine = RuleEngine([r1, r2])
    evt = create_mock_event()
    res = engine.evaluate(evt)
    
    assert len(res) == 2
