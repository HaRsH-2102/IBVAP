import sys
import os
import pytest
from datetime import datetime
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.security import SecurityEvent, AlertStatus
from app.domain.rule import Severity
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.repositories import AlertRepository
from app.event.alert_manager import AlertManager

@pytest.fixture
def db():
    # Use in-memory DB for tests
    database = SQLiteDatabase(db_path=":memory:")
    yield database
    database.close()

def create_mock_sec_event(event_id="e1", cam="cam1", track="t1", rule="r1", obj="z1"):
    return SecurityEvent(
        event_id=event_id,
        event_type="INTRUSION",
        severity=Severity.HIGH,
        camera_id=cam,
        track_id=track,
        source_spatial_event_id="s1",
        rule_id=rule,
        timestamp=datetime.utcnow(),
        metadata={"spatial_event": {"spatial_object_id": obj}}
    )

def test_alert_deduplication(db):
    repo = AlertRepository(db)
    manager = AlertManager(repo)
    
    # 1. First event -> New Alert
    e1 = create_mock_sec_event("e1")
    alerts1 = manager.process_events([e1])
    assert len(alerts1) == 1
    alert_id = alerts1[0].alert_id
    
    # Verify in DB
    saved_alert = repo.get_active_alert_by_dedup_key(manager._generate_dedup_key(e1, "z1"))
    assert saved_alert is not None
    assert saved_alert.alert_id == alert_id
    assert len(saved_alert.security_event_ids) == 1
    
    # 2. Same condition occurs again -> Deduplicated (updated, no new alert returned)
    e2 = create_mock_sec_event("e2")
    alerts2 = manager.process_events([e2])
    assert len(alerts2) == 0 # no NEW alert
    
    # Verify DB updated
    saved_alert = repo.get_active_alert_by_dedup_key(manager._generate_dedup_key(e2, "z1"))
    assert len(saved_alert.security_event_ids) == 2
    assert "e2" in saved_alert.security_event_ids

def test_alert_reopening(db):
    repo = AlertRepository(db)
    manager = AlertManager(repo)
    
    # 1. First event
    e1 = create_mock_sec_event("e1")
    alerts1 = manager.process_events([e1])
    alert = alerts1[0]
    
    # 2. Resolve alert
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    repo.save_alert(alert)
    
    # 3. Same condition occurs again -> New Alert (because old is RESOLVED)
    e3 = create_mock_sec_event("e3")
    alerts3 = manager.process_events([e3])
    assert len(alerts3) == 1 # A new alert is generated
    assert alerts3[0].alert_id != alert.alert_id
