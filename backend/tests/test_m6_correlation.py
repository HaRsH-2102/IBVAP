import sys
import os
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.security import SecurityEvent
from app.domain.rule import Rule, CorrelationPolicy, Severity
from app.event.correlator import BasicCorrelator

def create_mock_sec_event(event_id, cam, track, ts, rule_id):
    return SecurityEvent(
        event_id=event_id,
        event_type="INTRUSION",
        severity=Severity.LOW,
        camera_id=cam,
        track_id=track,
        source_spatial_event_id="s1",
        rule_id=rule_id,
        timestamp=ts,
    )

def test_basic_correlation():
    r1 = Rule(
        rule_id="r1", name="R1", security_event_type="SE", severity=Severity.LOW,
        correlation_policy=CorrelationPolicy(enabled=True, window_seconds=5)
    )
    
    correlator = BasicCorrelator([r1])
    
    base_ts = datetime.utcnow()
    
    # 1. Two events within 5 seconds for the same track/cam -> Same correlation ID
    e1 = create_mock_sec_event("e1", "cam1", "t1", base_ts, "r1")
    e2 = create_mock_sec_event("e2", "cam1", "t1", base_ts + timedelta(seconds=2), "r1")
    
    res = correlator.correlate([e1, e2])
    assert len(res) == 2
    assert res[0].correlation_id is not None
    assert res[0].correlation_id == res[1].correlation_id
    
    # 2. Event for different track -> Different correlation ID
    e3 = create_mock_sec_event("e3", "cam1", "t2", base_ts, "r1")
    res2 = correlator.correlate([e3])
    assert res2[0].correlation_id != res[0].correlation_id
    
    # 3. Event beyond 5 seconds -> Different correlation ID
    e4 = create_mock_sec_event("e4", "cam1", "t1", base_ts + timedelta(seconds=6), "r1")
    res3 = correlator.correlate([e4])
    assert res3[0].correlation_id != res[0].correlation_id
