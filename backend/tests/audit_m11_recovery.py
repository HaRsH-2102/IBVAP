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
from app.evidence.artifact_reconciliation import ArtifactReconciliation

def test_recovery():
    print("====================================")
    print("M11 RECOVERY AUDIT")
    print("====================================")
    
    db_path = "m11_recovery.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = SQLiteDatabase(db_path)
    repo = SQLiteClipRepository(db)
    
    storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "m11", "recovery"))
    os.makedirs(storage_dir, exist_ok=True)
    
    config = SystemConfiguration(
        storage_base_path=storage_dir,
        pre_event_seconds=5,
        post_event_seconds=5,
        incident_clip_enabled=True,
        thumbnail_enabled=True
    )
    
    renderer = EvidenceRenderer()
    worker = ClipWorker(config, repo, renderer)
    worker.start()
    
    video_path = "C:\\Users\\Harshal\\Downloads\\videoplayback.mp4"
    
    # ----------------------------------------------------
    # FIX 1: Per-Frame Track Annotation
    # ----------------------------------------------------
    print("\n--- Testing Per-Frame Annotation ---")
    
    # Create fake trajectory mapping (box moving across screen)
    # The video has 25 fps, event is at frame 500 (t=20s).
    # Pre_event = 5s (125 frames), Post_event = 5s (125 frames) -> Frames 375 to 625
    fake_trajectory = []
    x1, y1, x2, y2 = 100, 100, 200, 200
    for f_idx in range(375, 626):
        fake_trajectory.append({
            "frame_index": f_idx,
            "bounding_box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        })
        x1 += 2
        x2 += 2
        
    evt_track = SecurityEvent(
        event_id=str(uuid.uuid4()), event_type="ZONE_ENTER", severity=SeverityLevel.HIGH,
        camera_id="cam_track", track_id="track-1", source_spatial_event_id="sp", rule_id="rule",
        timestamp=datetime.now(timezone.utc), description="Moving vehicle",
        metadata={
            "frame_index": 500,
            "trajectory": fake_trajectory
        }
    )
    evd_track = EvidencePackage(evidence_id=str(uuid.uuid4()), security_event_id=evt_track.event_id, camera_id="cam_track", event_type="ZONE_ENTER", timestamp=evt_track.timestamp, status=EvidenceStatus.PERSISTED)
    worker.enqueue(ClipRequest(evt_track, evd_track, video_path))
    
    # ----------------------------------------------------
    # FIX 3: Partial Clip Logic
    # ----------------------------------------------------
    print("\n--- Testing Partial Clip Logic ---")
    # Event at frame 10 (t=0.4s). Pre-event = 5s (125 frames). Requested start = -115 -> PARTIAL
    evt_partial = SecurityEvent(
        event_id=str(uuid.uuid4()), event_type="ZONE_ENTER", severity=SeverityLevel.HIGH,
        camera_id="cam_partial", track_id="track-2", source_spatial_event_id="sp", rule_id="rule",
        timestamp=datetime.now(timezone.utc), description="Partial start",
        metadata={"frame_index": 10}
    )
    evd_partial = EvidencePackage(evidence_id=str(uuid.uuid4()), security_event_id=evt_partial.event_id, camera_id="cam_partial", event_type="ZONE_ENTER", timestamp=evt_partial.timestamp, status=EvidenceStatus.PERSISTED)
    worker.enqueue(ClipRequest(evt_partial, evd_partial, video_path))
    
    # Event at frame 500 (t=20s). Source has 1191 frames. Request 375 to 625 -> NOT PARTIAL (ENCODING -> PERSISTED)
    evt_full = SecurityEvent(
        event_id=str(uuid.uuid4()), event_type="ZONE_ENTER", severity=SeverityLevel.HIGH,
        camera_id="cam_full", track_id="track-3", source_spatial_event_id="sp", rule_id="rule",
        timestamp=datetime.now(timezone.utc), description="Full clip",
        metadata={"frame_index": 500}
    )
    evd_full = EvidencePackage(evidence_id=str(uuid.uuid4()), security_event_id=evt_full.event_id, camera_id="cam_full", event_type="ZONE_ENTER", timestamp=evt_full.timestamp, status=EvidenceStatus.PERSISTED)
    worker.enqueue(ClipRequest(evt_full, evd_full, video_path))
    
    # Wait for processing
    print("Waiting for workers to finish (up to 40 seconds)...")
    for _ in range(40):
        c1 = repo.get_by_security_event_id(evt_track.event_id)
        c2 = repo.get_by_security_event_id(evt_partial.event_id)
        c3 = repo.get_by_security_event_id(evt_full.event_id)
        
        c1_done = c1 and c1.status in [ClipStatus.PERSISTED, ClipStatus.PARTIAL]
        c2_done = c2 and c2.status in [ClipStatus.PERSISTED, ClipStatus.PARTIAL]
        c3_done = c3 and c3.status in [ClipStatus.PERSISTED, ClipStatus.PARTIAL]
        
        if c1_done and c2_done and c3_done:
            break
        time.sleep(1)
        
    worker.stop()
    
    c1 = repo.get_by_security_event_id(evt_track.event_id)
    c2 = repo.get_by_security_event_id(evt_partial.event_id)
    c3 = repo.get_by_security_event_id(evt_full.event_id)
    
    print(f"Per-Frame clip status: {c1.status.value if c1 else 'NOT FOUND'}")
    print(f"Partial clip status: {c2.status.value if c2 else 'NOT FOUND'}")
    print(f"Full clip status: {c3.status.value if c3 else 'NOT FOUND'}")
    
    # ----------------------------------------------------
    # Verify Per-Frame extraction
    # ----------------------------------------------------
    if c1 and os.path.exists(c1.clip_path):
        cap = cv2.VideoCapture(c1.clip_path)
        out_dir = os.path.join(storage_dir, "per_frame_annotation")
        os.makedirs(out_dir, exist_ok=True)
        
        frames_to_save = [0, 50, 125, 200, 240]
        for f_idx in frames_to_save:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(os.path.join(out_dir, f"frame_{f_idx}.jpg"), frame)
        cap.release()
        print(f"Extracted annotated frames to {out_dir}")
        
    # ----------------------------------------------------
    # FIX 2: Artifact Reconciliation
    # ----------------------------------------------------
    print("\n--- Testing Artifact Reconciliation ---")
    
    # DB + MP4 + Thumb (VALID) -> c1, c2, c3 should be VALID
    
    # DB row + missing MP4 (ARTIFACT_MISSING)
    evt_miss = SecurityEvent(event_id=str(uuid.uuid4()), event_type="ZONE_ENTER", severity=SeverityLevel.HIGH, camera_id="cam_miss", track_id="track", source_spatial_event_id="sp", rule_id="r", timestamp=datetime.now(timezone.utc), description="")
    repo.create_clip(IncidentClip(clip_id=str(uuid.uuid4()), security_event_id=evt_miss.event_id, camera_id="cam_miss", event_type="ZONE", event_timestamp=evt_miss.timestamp, status=ClipStatus.PERSISTED, clip_path="nonexistent.mp4"))
    
    # Orphaned MP4
    orphan_dir = os.path.join(storage_dir, "evidence", "orphan_cam", "2026-08-26", "orphan_evd")
    os.makedirs(orphan_dir, exist_ok=True)
    orphan_file = os.path.join(orphan_dir, "incident_clip.mp4")
    with open(orphan_file, "w") as f: f.write("fake video")
    
    reconciler = ArtifactReconciliation(db, storage_dir)
    results = reconciler.reconcile()
    
    for res in results:
        print(f"{res.status}: {res.message} (Event: {res.security_event_id})")

if __name__ == "__main__":
    test_recovery()
