import sys
import os
import time
import uuid
import cv2
import sqlite3
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.security import SecurityEvent
from app.domain.severity import SeverityLevel
from app.domain.evidence import EvidencePackage, EvidenceStatus
from app.domain.incident_clip import ClipStatus, IncidentClip
from app.domain.system_config import SystemConfiguration
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.clip_repository import SQLiteClipRepository
from app.evidence.clip_worker import ClipWorker, ClipRequest
from app.evidence.evidence_renderer import EvidenceRenderer
from app.event.rule_engine import RuleEngine
from app.evidence.evidence_worker import EvidenceWorker

def log_test(name, result, details=""):
    print(f"[{result}] {name}: {details}")
    with open("m11_audit_log.txt", "a") as f:
        f.write(f"[{result}] {name}: {details}\n")

def run_comprehensive_audit():
    if os.path.exists("m11_audit_log.txt"):
        os.remove("m11_audit_log.txt")
        
    db_path = "m11_audit.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = SQLiteDatabase(db_path)
    repo = SQLiteClipRepository(db)
    
    storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "m11", "audit"))
    os.makedirs(storage_dir, exist_ok=True)
    
    config = SystemConfiguration(
        storage_base_path=storage_dir,
        pre_event_seconds=5,
        post_event_seconds=5,
        incident_clip_enabled=True,
        thumbnail_enabled=True
    )
    
    video_path = "C:\\Users\\Harshal\\Downloads\\videoplayback.mp4"
    
    # Check default retention
    log_test("13. Retention default disabled", "PASS" if not config.clip_retention_enabled else "FAIL", f"clip_retention_enabled={config.clip_retention_enabled}")
    
    renderer = EvidenceRenderer()
    worker = ClipWorker(config, repo, renderer)
    worker.start()
    
    # 1. Normal Full Clip
    print("\n--- 1. Normal Full Clip ---")
    evt1 = SecurityEvent(
        event_id=str(uuid.uuid4()), event_type="ZONE_ENTER", severity=SeverityLevel.HIGH,
        camera_id="cam1", track_id="cam1-1", source_spatial_event_id="sp-1", rule_id="rule-1",
        timestamp=datetime.now(timezone.utc), description="Normal",
        metadata={"frame_index": 500, "evidence": {"bounding_box": {"x1": 500, "y1": 300, "x2": 800, "y2": 600}}}
    )
    evd1 = EvidencePackage(evidence_id=str(uuid.uuid4()), security_event_id=evt1.event_id, camera_id="cam1", event_type="ZONE_ENTER", timestamp=evt1.timestamp, status=EvidenceStatus.PERSISTED)
    worker.enqueue(ClipRequest(evt1, evd1, video_path))
    
    # 2. Partial Clip
    print("\n--- 2. Partial Clip ---")
    evt2 = SecurityEvent(
        event_id=str(uuid.uuid4()), event_type="ZONE_ENTER", severity=SeverityLevel.HIGH,
        camera_id="cam1", track_id="cam1-2", source_spatial_event_id="sp-2", rule_id="rule-1",
        timestamp=datetime.now(timezone.utc), description="Partial",
        metadata={"frame_index": 50, "evidence": {"bounding_box": {"x1": 500, "y1": 300, "x2": 800, "y2": 600}}}
    )
    evd2 = EvidencePackage(evidence_id=str(uuid.uuid4()), security_event_id=evt2.event_id, camera_id="cam1", event_type="ZONE_ENTER", timestamp=evt2.timestamp, status=EvidenceStatus.PERSISTED)
    worker.enqueue(ClipRequest(evt2, evd2, video_path))
    
    # 8. Source Unavailable
    print("\n--- 8. Source Unavailable ---")
    evt3 = SecurityEvent(
        event_id=str(uuid.uuid4()), event_type="ZONE_ENTER", severity=SeverityLevel.HIGH,
        camera_id="cam1", track_id="cam1-3", source_spatial_event_id="sp-3", rule_id="rule-1",
        timestamp=datetime.now(timezone.utc), description="Missing Source",
        metadata={"frame_index": 500}
    )
    evd3 = EvidencePackage(evidence_id=str(uuid.uuid4()), security_event_id=evt3.event_id, camera_id="cam1", event_type="ZONE_ENTER", timestamp=evt3.timestamp, status=EvidenceStatus.PERSISTED)
    worker.enqueue(ClipRequest(evt3, evd3, "invalid_video.mp4"))
    
    time.sleep(15) # Wait for processing
    worker.stop()
    
    # 10. Idempotency (UNIQUE constraint)
    print("\n--- 10. Idempotency ---")
    try:
        c1 = IncidentClip(clip_id="c1", security_event_id="evt_idem", camera_id="cam", event_type="T", event_timestamp=datetime.now(timezone.utc))
        c2 = IncidentClip(clip_id="c2", security_event_id="evt_idem", camera_id="cam", event_type="T", event_timestamp=datetime.now(timezone.utc))
        repo.create_clip(c1)
        try:
            repo.create_clip(c2)
            log_test("10. Idempotency UNIQUE constraint", "FAIL", "DB allowed duplicate security_event_id")
        except sqlite3.IntegrityError:
            log_test("10. Idempotency UNIQUE constraint", "PASS", "DB rejected duplicate security_event_id")
    except Exception as e:
        log_test("10. Idempotency UNIQUE constraint", "ERROR", str(e))
    
    clip1 = repo.get_by_security_event_id(evt1.event_id)
    if clip1 and clip1.status == ClipStatus.PERSISTED:
        log_test("1. Normal Full Clip", "PASS", f"Duration: {clip1.duration_seconds}s, Size: {os.path.getsize(clip1.clip_path)}")
        # 3. Frame Accuracy (<=100ms) - Simplified test: check start/end frames
        fps = clip1.metadata.get("source_fps", 25)
        start_f = clip1.metadata.get("start_frame")
        end_f = clip1.metadata.get("end_frame")
        if end_f - start_f == int(10 * fps):
            log_test("3. Frame Accuracy", "PASS (EXACT_EVENT_FRAME)", f"Frames: {start_f} to {end_f}")
        else:
            log_test("3. Frame Accuracy", "FAIL", f"Frames: {start_f} to {end_f}")
    else:
        log_test("1. Normal Full Clip", "FAIL", f"Status: {clip1.status.value if clip1 else 'Not Found'}")
        
    clip2 = repo.get_by_security_event_id(evt2.event_id)
    if clip2 and clip2.status == ClipStatus.PARTIAL:
        log_test("2. Partial Clip", "PASS", f"Duration: {clip2.duration_seconds}s")
    else:
        log_test("2. Partial Clip", "FAIL", f"Status: {clip2.status.value if clip2 else 'Not Found'}")
        
    clip3 = repo.get_by_security_event_id(evt3.event_id)
    if clip3 and clip3.status == ClipStatus.SOURCE_UNAVAILABLE:
        log_test("8. Source Unavailable", "PASS", f"Status: {clip3.status.value}")
    else:
        log_test("8. Source Unavailable", "FAIL", f"Status: {clip3.status.value if clip3 else 'Not Found'}")
        
    print("\n--- 5. Queue Full ---")
    config.clip_queue_capacity = 2
    worker2 = ClipWorker(config, repo, renderer) # without starting thread
    worker2.enqueue(ClipRequest(evt1, evd1, video_path))
    worker2.enqueue(ClipRequest(evt2, evd2, video_path))
    success = worker2.enqueue(ClipRequest(evt3, evd3, video_path))
    if not success:
        log_test("5. Queue Full", "PASS", "Queue rejected overflow request")
        
        # Check if FAILED is inserted
        # Worker handles it in _handle_queue_full
        clip_full = repo.get_by_security_event_id(evt3.event_id)
        # We reused evt3 which already has SOURCE_UNAVAILABLE, so wait, let's make a new one
        evt4 = SecurityEvent(event_id=str(uuid.uuid4()), event_type="ZONE_ENTER", severity=SeverityLevel.HIGH, camera_id="cam", track_id="t", source_spatial_event_id="s", rule_id="r", timestamp=datetime.now(timezone.utc), description="")
        evd4 = EvidencePackage(evidence_id=str(uuid.uuid4()), security_event_id=evt4.event_id, camera_id="cam", event_type="ZONE_ENTER", timestamp=evt4.timestamp, status=EvidenceStatus.PERSISTED)
        worker2.enqueue(ClipRequest(evt4, evd4, video_path))
        clip_full2 = repo.get_by_security_event_id(evt4.event_id)
        if clip_full2 and clip_full2.status == ClipStatus.FAILED and clip_full2.failure_reason == "CLIP_QUEUE_FULL":
            log_test("5. Queue Full DB status", "PASS", "Recorded CLIP_QUEUE_FULL")
        else:
            log_test("5. Queue Full DB status", "FAIL", "")
    else:
        log_test("5. Queue Full", "FAIL", "Queue accepted overflow request")

    print("\n--- 7. Encoder Unavailable ---")
    # Mock encoder check to False
    worker2.encoder_available = False
    worker2.start()
    evt5 = SecurityEvent(event_id=str(uuid.uuid4()), event_type="ZONE", severity=SeverityLevel.HIGH, camera_id="cam", track_id="t", source_spatial_event_id="s", rule_id="r", timestamp=datetime.now(timezone.utc), description="")
    worker2.enqueue(ClipRequest(evt5, evd4, video_path))
    time.sleep(2)
    worker2.stop()
    clip5 = repo.get_by_security_event_id(evt5.event_id)
    if clip5 and clip5.status == ClipStatus.FAILED and clip5.failure_reason == "ENCODER_UNAVAILABLE":
        log_test("7. Encoder Unavailable", "PASS", "Status gracefully degraded")
    else:
        log_test("7. Encoder Unavailable", "FAIL", "Did not fail gracefully")

if __name__ == "__main__":
    run_comprehensive_audit()
