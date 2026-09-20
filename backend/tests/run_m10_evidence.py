import os
import sys
import time
import cv2
import uuid
from datetime import datetime, timezone

# Ensure backend root is in Python path when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.system_config import SystemConfiguration
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.evidence_repository import LocalEvidenceRepository
from app.infrastructure.evidence_storage import EvidenceStorage
from app.evidence.evidence_renderer import EvidenceRenderer
from app.evidence.evidence_worker import EvidenceWorker, EvidenceRequest
from app.domain.security import SecurityEvent
from app.domain.rule import Severity

def run_m10_validation():
    print("="*60)
    print("M10 EVIDENCE & EVENT INTELLIGENCE VALIDATION")
    print("="*60)
    
    # 1. Setup Architecture
    config = SystemConfiguration(
        storage_base_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "m10")),
        evidence_enabled=True,
        evidence_queue_capacity=50
    )
    
    # Use an in-memory DB or a specific file for validation
    db_path = os.path.join(config.storage_base_path, "m10_validation.db")
    os.makedirs(config.storage_base_path, exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = SQLiteDatabase(db_path)
    repo = LocalEvidenceRepository(db)
    storage = EvidenceStorage(config)
    renderer = EvidenceRenderer()
    
    worker = EvidenceWorker(config, repo, storage, renderer)
    worker.start()
    
    # 2. Extract a frame from the Daytime video
    video_path = r"C:\Users\Harshal\Downloads\The CCTV People Demo 2.mp4"
    print(f"Loading video from: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("ERROR: Could not open video file.")
        worker.stop()
        return
        
    # Read a few frames deep to get a good image
    for _ in range(50):
        ret, frame = cap.read()
    cap.release()
    
    if frame is None:
        print("ERROR: Could not read frame from video.")
        worker.stop()
        return

    # 3. Simulate an M6 Security Event
    event_id = str(uuid.uuid4())
    print(f"\nSimulating M6 SecurityEvent: {event_id}")
    
    # Draw a fake bounding box in the middle of the frame
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    box_w, box_h = 100, 150
    bbox = {
        "x1": cx - box_w // 2,
        "y1": cy - box_h // 2,
        "x2": cx + box_w // 2,
        "y2": cy + box_h // 2
    }
    
    sec_event = SecurityEvent(
        event_id=event_id,
        event_type="LOITERING_DETECTED",
        severity=Severity.HIGH,
        camera_id="cam_main_gate",
        track_id="trk-99",
        source_spatial_event_id="sp-101",
        rule_id="rule-loit",
        timestamp=datetime.now(timezone.utc),
        metadata={
            "evidence": {"bounding_box": bbox},
            "object_class": "person",
            "dwell_seconds": 65.4,
            "zone_id": "zone_secure_01"
        }
    )
    
    # 4. Enqueue to Evidence Worker
    print("Enqueueing EvidenceRequest...")
    success = worker.enqueue(EvidenceRequest(sec_event, frame))
    print(f"Enqueue success: {success}")
    
    # 5. Wait for asynchronous processing
    print("Waiting for EvidenceWorker to process...")
    time.sleep(2.0)
    
    # 6. Validate results
    saved = repo.get_by_security_event_id(event_id)
    if saved:
        print("\n--- Validation Success ---")
        print(f"Status: {saved.status.value}")
        print(f"Evidence ID: {saved.evidence_id}")
        print(f"Original Path: {saved.original_frame_path}")
        print(f"Annotated Path: {saved.annotated_frame_reference}")
        print("\nPlease inspect the artifacts/m10/ directory for the output images.")
    else:
        print("\n--- Validation Failed ---")
        print("Evidence package was not found in the database.")
        
    print(f"\nWorker Metrics: {worker.metrics}")
    
    worker.stop()
    db.close()
    
if __name__ == "__main__":
    run_m10_validation()
