import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime, timezone
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker

from app.domain.zone import Zone, Point, ZoneType
from app.domain.virtual_line import VirtualLine, Direction
from app.domain.spatial import CameraSpatialConfig
from app.spatial.spatial_engine import SpatialEngine

from app.behavioral.engine import BehavioralEngine
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.loitering import LoiteringDetector
from app.anpr.anpr_engine import ANPREngine

from app.domain.rule import Rule, Severity
from app.event.rule_engine import RuleEngine
from app.event.alert_manager import AlertManager
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.repositories import SecurityEventRepository, AlertRepository

from app.infrastructure.clip_repository import SQLiteClipRepository
from app.evidence.clip_worker import ClipWorker, ClipRequest
from app.evidence.evidence_renderer import EvidenceRenderer
from app.domain.system_config import SystemConfiguration
from app.domain.evidence import EvidencePackage, EvidenceStatus

def run_demo(video_path: str):
    print("Initializing IBVAP M1-M12 E2E Pipeline...")
    camera_id = "cam_test_01"
    
    settings.playback_mode = "real_time"
    metrics = StreamMetrics(window_size=30)
    
    stream_manager = FileStreamManager(camera_id, video_path)
    pipeline = CameraPipeline(stream_manager, metrics)
    
    detector = YOLODetector(model_path="yolov8n.pt", confidence_threshold=0.25, inference_size=640, device="auto")
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    
    # Very big zone to ensure triggers
    zone1 = Zone(
        zone_id="restricted_zone",
        camera_id=camera_id,
        name="Restricted Area",
        zone_type=ZoneType.RESTRICTED,
        geometry=[Point(x=0, y=0), Point(x=1920, y=0), Point(x=1920, y=1080), Point(x=0, y=1080)]
    )
    spatial_config = CameraSpatialConfig(camera_id=camera_id, zones=[zone1], tripwires=[])
    spatial_engine = SpatialEngine()
    
    b_config = BehavioralConfig(loitering_duration=3.0)
    behavioral_engine = BehavioralEngine(b_config, [LoiteringDetector()])
    from app.anpr.anpr_service import ANPRService
    anpr_service = ANPRService(SystemConfiguration(), SQLiteDatabase())
    anpr_service.start()
    
    db = SQLiteDatabase()
    sec_repo = SecurityEventRepository(db)
    alert_repo = AlertRepository(db)
    alert_manager = AlertManager(alert_repo)
    
    rule = Rule(
        rule_id="r1", name="Intrusion Detection", enabled=True,
        security_event_type="ZONE_ENTER", severity=Severity.CRITICAL, event_type=["ZONE_ENTER"]
    )
    rule_engine = RuleEngine([rule])
    
    # Clip Worker
    storage_dir = os.path.abspath("storage")
    os.makedirs(storage_dir, exist_ok=True)
    sys_config = SystemConfiguration(storage_base_path=storage_dir, pre_event_seconds=2, post_event_seconds=2, incident_clip_enabled=True, thumbnail_enabled=True)
    clip_repo = SQLiteClipRepository(db)
    clip_worker = ClipWorker(sys_config, clip_repo, EvidenceRenderer())
    clip_worker.start()
    
    pipeline.start()
    time.sleep(1.0)
    print("Pipeline Started. Wait for events...")
    
    active_alerts = 0
    
    try:
        while pipeline.is_running:
            frame = pipeline.get_next_frame(timeout=0.1)
            if frame:
                current_time = datetime.now(timezone.utc)
                
                detections = detector.detect(frame)
                tracks = tracker.update(detections, frame)
                
                spatial_events = spatial_engine.process(tracks, spatial_config)
                behavioral_events = behavioral_engine.process(tracks, spatial_events, current_time)
                # Old ANPR Engine removed: anpr_events = anpr.process(...)
                
                # Save latest frame for M12 live dashboard snapshot
                latest_frame_path = os.path.abspath(os.path.join(storage_dir, f"latest_{camera_id}.jpg"))
                
                # We need to annotate the frame slightly for the live demo if we want
                vis_img = frame.data.copy()
                for t in tracks:
                    if t.state.value != "ACTIVE": continue
                    left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                    cv2.rectangle(vis_img, (left, top), (right, bottom), (0, 255, 0), 2)
                    
                cv2.imwrite(latest_frame_path, vis_img)
                

                sec_events = []
                for e in spatial_events: sec_events.extend(rule_engine.evaluate(e))
                for e in behavioral_events: sec_events.extend(rule_engine.evaluate(e))
                
                for se in sec_events:
                    # Inject bounding box for ANPR matching benchmark expectation
                    for t in tracks:
                        if t.track_id == se.track_id:
                            if "evidence" not in se.metadata:
                                se.metadata["evidence"] = {}
                            se.metadata["evidence"]["bounding_box"] = {
                                "x1": int(t.bounding_box.left),
                                "y1": int(t.bounding_box.top),
                                "x2": int(t.bounding_box.right),
                                "y2": int(t.bounding_box.bottom)
                            }
                            se.metadata["object_class"] = t.object_class.value if hasattr(t.object_class, 'value') else str(t.object_class)
                            break
                            
                    sec_repo.save(se)
                    
                    # Generate Evidence Package mockup so clip worker doesn't fail
                    evidence_path = os.path.abspath(os.path.join(storage_dir, f"evidence_{se.event_id}.jpg"))
                    cv2.imwrite(evidence_path, frame.data)
                    conn = db.get_connection()
                    conn.execute("INSERT OR IGNORE INTO evidence_packages (evidence_id, security_event_id, status, annotated_frame_reference) VALUES (?, ?, ?, ?)", 
                                (str(uuid.uuid4()), se.event_id, EvidenceStatus.PERSISTED.value, evidence_path))
                    conn.commit()
                    
                    # Trigger ANPR
                    anpr_service.enqueue_job(se, frame.data)
                    
                    # Trigger Clip Worker
                    evd = EvidencePackage(evidence_id="mock", security_event_id=se.event_id, camera_id=se.camera_id, event_type=se.event_type, timestamp=se.timestamp, status=EvidenceStatus.PERSISTED)
                    clip_worker.enqueue(ClipRequest(se, evd, video_path))
                    
                new_alerts = alert_manager.process_events(sec_events)
                if new_alerts:
                    print(f"Generated {len(new_alerts)} new alerts! ID: {new_alerts[0].alert_id}")
                    active_alerts += len(new_alerts)
                    
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.stop()
        clip_worker.stop()
        anpr_service.stop()
        print("Demo finished.")

if __name__ == "__main__":
    video = "test_video.mp4"
    if len(sys.argv) > 1:
        video = sys.argv[1]
    
    if not os.path.exists(video):
        print(f"File not found: {video}")
    else:
        print(f"Starting pipeline for video: {video}")
        run_demo(video)
