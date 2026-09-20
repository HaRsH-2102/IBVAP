import os
import sys
import uuid
import json
from datetime import datetime, timezone
import sqlite3
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.infrastructure.database import SQLiteDatabase
from app.domain.incident_clip import ClipStatus
from app.domain.evidence import EvidenceStatus

def run_m12_audit():
    print("====================================")
    print("M12 COMMAND CENTER AUDIT")
    print("====================================")
    
    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 1. Synthesize Data
    evt_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())
    clip_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
        INSERT OR IGNORE INTO security_events 
        (event_id, event_type, severity, camera_id, track_id, timestamp, metadata)
        VALUES (?, 'ZONE_ENTER', 'HIGH', 'cam_test_01', 'track_1', ?, ?)
    """, (evt_id, now, json.dumps({"frame_index": 100})))
    
    cursor.execute("""
        INSERT OR IGNORE INTO alerts
        (alert_id, severity, event_type, camera_id, track_id, status, title, created_at, security_event_ids)
        VALUES (?, 'HIGH', 'ZONE_ENTER', 'cam_test_01', 'track_1', 'OPEN', 'Restricted Zone Entry', ?, ?)
    """, (alert_id, now, json.dumps([evt_id])))
    
    # Ensure evidence exists on disk for test
    evidence_path = os.path.abspath("storage/test_evidence.jpg")
    with open(evidence_path, "w") as f: f.write("fake_image_data")
    
    cursor.execute("""
        INSERT OR IGNORE INTO evidence_packages
        (evidence_id, security_event_id, status, annotated_frame_reference)
        VALUES (?, ?, ?, ?)
    """, (evidence_id, evt_id, EvidenceStatus.PERSISTED.value, evidence_path))
    
    clip_path = os.path.abspath("storage/test_clip.mp4")
    with open(clip_path, "w") as f: f.write("fake_mp4_video_data_longer_to_test_range_requests")
    
    cursor.execute("""
        INSERT OR IGNORE INTO incident_clips
        (clip_id, security_event_id, status, clip_path)
        VALUES (?, ?, ?, ?)
    """, (clip_id, evt_id, ClipStatus.PERSISTED.value, clip_path))
    
    conn.commit()
    
    # 2. Test API using TestClient
    client = TestClient(app)
    
    print("\n--- Testing Camera API ---")
    res = client.get("/api/v1/cameras")
    assert res.status_code == 200
    cams = res.json()
    print("Cameras:", len(cams))
    
    print("\n--- Testing Alerts API ---")
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200
    alerts = res.json()
    print("Alerts:", len(alerts))
    
    res = client.get(f"/api/v1/alerts/{alert_id}")
    assert res.status_code == 200
    alert_detail = res.json()
    print("Alert detail contains evidence:", "evidence" in alert_detail)
    print("Alert detail contains clip:", "clip" in alert_detail)
    
    print("\n--- Testing Artifact Serving (Range) ---")
    res = client.get(f"/api/v1/clips/{clip_id}/video", headers={"Range": "bytes=0-10"})
    assert res.status_code == 206
    assert "Content-Range" in res.headers
    print("Range request successful! Content-Range:", res.headers["Content-Range"])
    
    print("\n--- Testing Alert Lifecycle ---")
    res = client.patch(f"/api/v1/alerts/{alert_id}/ack")
    assert res.status_code == 200
    assert res.json()["status"] == "ACKNOWLEDGED"
    print("Acknowledge successful.")
    
    res = client.patch(f"/api/v1/alerts/{alert_id}/resolve")
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"
    print("Resolve successful.")
    
    print("\nAll M12 API tests passed!")

if __name__ == "__main__":
    run_m12_audit()
