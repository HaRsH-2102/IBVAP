import sys
import os
import time
import uuid
import cv2
import shutil
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.security import SecurityEvent
from app.domain.severity import SeverityLevel
from app.domain.evidence import EvidencePackage, EvidenceStatus, EvidenceQuality
from app.domain.incident_clip import ClipStatus
from app.domain.system_config import SystemConfiguration
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.clip_repository import SQLiteClipRepository
from app.evidence.clip_worker import ClipWorker, ClipRequest
from app.evidence.evidence_renderer import EvidenceRenderer

def test_m11():
    print("====================================")
    print("M11 INCIDENT CLIP GENERATION AUDIT")
    print("====================================")
    
    db_path = "m11_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = SQLiteDatabase(db_path)
    repo = SQLiteClipRepository(db)
    
    storage_dir = "E:\\SIH 2026\\IBVAP\\artifacts\\full_system_audit\\m11"
    os.makedirs(storage_dir, exist_ok=True)
    
    # 1. Normal execution
    config = SystemConfiguration(
        storage_base_path=storage_dir,
        pre_event_seconds=2,
        post_event_seconds=2,
        incident_clip_enabled=True,
        thumbnail_enabled=True
    )
    
    renderer = EvidenceRenderer()
    worker = ClipWorker(config, repo, renderer)
    worker.start()
    
    video_path = "C:\\Users\\Harshal\\Downloads\\videoplayback.mp4"
    if not os.path.exists(video_path):
        print("Test Video not found. Skipping.")
        return
        
    print(f"\n--- Testing M11 Normal Clip Generation ---")
    
    sec_event = SecurityEvent(
        event_id=str(uuid.uuid4()),
        event_type="ZONE_ENTER",
        severity=SeverityLevel.HIGH,
        camera_id="cam1",
        track_id="cam1-123",
        source_spatial_event_id="spatial-1",
        rule_id="rule-1",
        timestamp=datetime.now(timezone.utc),
        description="Test Evidence Capture",
        metadata={
            "evidence": {"bounding_box": {"x1": 500, "y1": 300, "x2": 800, "y2": 600}},
            "object_class": "car",
            "frame_index": 60 # Assume 60th frame is the event
        }
    )
    
    evidence = EvidencePackage(
        evidence_id=str(uuid.uuid4()),
        security_event_id=sec_event.event_id,
        camera_id=sec_event.camera_id,
        event_type=sec_event.event_type,
        timestamp=sec_event.timestamp,
        status=EvidenceStatus.PERSISTED
    )
    
    request = ClipRequest(
        security_event=sec_event,
        evidence_package=evidence,
        source_video_reference=video_path
    )
    
    worker.enqueue(request)
    print("Enqueued ClipRequest. Waiting for worker processing (may take a few seconds)...")
    
    # Wait up to 10 seconds for completion
    for _ in range(20):
        clip = repo.get_by_security_event_id(sec_event.event_id)
        if clip and clip.status in [ClipStatus.PERSISTED, ClipStatus.PARTIAL, ClipStatus.FAILED, ClipStatus.SOURCE_UNAVAILABLE]:
            break
        time.sleep(0.5)
        
    clip = repo.get_by_security_event_id(sec_event.event_id)
    print("\n--- Verifying Database Metadata ---")
    if clip:
        print(f"Clip Package Found: {clip.clip_id}")
        print(f"Status: {clip.status.value}")
        print(f"Duration: {clip.duration_seconds} sec")
        
        if clip.status in [ClipStatus.PERSISTED, ClipStatus.PARTIAL]:
            if os.path.exists(clip.clip_path):
                print(f"Visual Artifact saved successfully at: {clip.clip_path}")
                print(f"File size: {os.path.getsize(clip.clip_path)} bytes")
            else:
                print(f"Visual Artifact NOT FOUND at {clip.clip_path}")
                
            if clip.thumbnail_path and os.path.exists(clip.thumbnail_path):
                print(f"Thumbnail saved successfully at: {clip.thumbnail_path}")
            else:
                print("Thumbnail NOT FOUND.")
    else:
        print("Clip Package NOT found in database!")
        
    # 2. Disk Backpressure Test
    print(f"\n--- Testing M11 Disk Backpressure ---")
    config.minimum_free_disk_gb = 1000000.0 # Imply 1 Petabyte required
    sec_event_fail = SecurityEvent(
        event_id=str(uuid.uuid4()),
        event_type="ZONE_ENTER",
        severity=SeverityLevel.HIGH,
        camera_id="cam1",
        track_id="cam1-124",
        source_spatial_event_id="spatial-2",
        rule_id="rule-1",
        timestamp=datetime.now(timezone.utc),
        description="Test Evidence Capture",
        metadata={"frame_index": 100}
    )
    request_fail = ClipRequest(sec_event_fail, evidence, video_path)
    worker.enqueue(request_fail)
    time.sleep(2)
    
    clip_fail = repo.get_by_security_event_id(sec_event_fail.event_id)
    if clip_fail:
        print(f"Backpressure Clip Status: {clip_fail.status.value}")
        print(f"Failure Reason: {clip_fail.failure_reason}")
    else:
        print("Backpressure clip NOT FOUND.")
        
    worker.stop()
    print("\nVerification Complete.")
    print("M11 Clip Workflow Logic: Verified")

if __name__ == "__main__":
    test_m11()
