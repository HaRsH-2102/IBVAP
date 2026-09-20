"""
IBVAP — Milestone 6 Integration Validation
==========================================
Runs the complete M1->M6 pipeline on a video file.
Includes YOLO (M3), ByteTrack (M4), Spatial (M5), and Event Interpretation (M6).
"""

import sys
import time
import argparse
import os
import cv2
import numpy as np

# Ensure backend root is in Python path when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.config import settings
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker

from app.domain.spatial import CameraSpatialConfig
from app.domain.zone import Zone, Point, ZoneType
from app.domain.virtual_line import VirtualLine, Direction
from app.spatial.spatial_engine import SpatialEngine

from app.event.config import load_rules
from app.event.rule_engine import RuleEngine
from app.event.correlator import BasicCorrelator
from app.event.alert_manager import AlertManager
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.repositories import SecurityEventRepository, AlertRepository
from app.infrastructure.evidence_repository import LocalEvidenceRepository
from app.infrastructure.evidence_storage import EvidenceStorage
from app.evidence.evidence_renderer import EvidenceRenderer
from app.evidence.evidence_service import EvidenceService
from app.domain.system_config import SystemConfiguration
from app.event.pipeline import M6EventPipeline

def create_synthetic_config(camera_id: str) -> CameraSpatialConfig:
    zone1 = Zone(
        zone_id="zone_01",
        camera_id=camera_id,
        name="Test Zone",
        zone_type=ZoneType.RESTRICTED,
        geometry=[
            Point(x=100, y=100),
            Point(x=1800, y=100),
            Point(x=1800, y=1500),
            Point(x=100, y=1500)
        ]
    )
    
    line1 = VirtualLine(
        line_id="line_01",
        camera_id=camera_id,
        name="Test Fence",
        start=Point(x=2000, y=200),
        end=Point(x=2000, y=1800),
        allowed_direction=Direction.BOTH
    )
    
    return CameraSpatialConfig(
        camera_id=camera_id,
        zones=[zone1],
        tripwires=[line1]
    )

def run_m6_test(video_path: str, inference_size: int, conf_thresh: float, no_show: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"Starting M6 Full Pipeline Validation:")
    print(f"Video: {video_path}")
    print(f"{'='*60}")
    
    settings.playback_mode = "real_time"
    camera_id = "cam_test_01"
    
    metrics = StreamMetrics(window_size=30)
    
    try:
        stream_manager = FileStreamManager(camera_id, video_path)
    except Exception as e:
        print(f"Failed to open video file: {e}")
        return
        
    detector = YOLODetector(
        model_path="yolov8n.pt",
        confidence_threshold=conf_thresh,
        inference_size=inference_size,
        device="auto" 
    )
    
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    spatial_engine = SpatialEngine(crossing_epsilon=3.0)
    spatial_config = create_synthetic_config(camera_id)

    # Initialize M6
    db = SQLiteDatabase("m6_test.db")
    sec_repo = SecurityEventRepository(db)
    alert_repo = AlertRepository(db)
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "m6_rules.yaml")
    rules = load_rules(config_path)
    rule_engine = RuleEngine(rules)
    correlator = BasicCorrelator(rules)
    alert_manager = AlertManager(alert_repo)
    
    # Initialize M10 Evidence
    config = SystemConfiguration(
        storage_base_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "m10")),
        evidence_enabled=True,
        evidence_queue_capacity=50
    )
    evidence_repo = LocalEvidenceRepository(db)
    evidence_storage = EvidenceStorage(config)
    evidence_renderer = EvidenceRenderer()
    evidence_service = EvidenceService(config, evidence_repo, evidence_storage, evidence_renderer)
    evidence_service.start()
    
    m6_pipeline = M6EventPipeline(rule_engine, correlator, alert_manager, sec_repo, evidence_service)

    pipeline = CameraPipeline(stream_manager, metrics)
    pipeline.start()
    
    print("Waiting for capture thread to warm up...")
    time.sleep(1.0)
    
    print("Draining warmup frames...")
    while True:
        f = pipeline.get_next_frame(timeout=0.0)
        if f is None:
            break
            
    metrics.reset()
    
    frames_processed = 0
    total_inference_time = 0.0
    total_tracker_time = 0.0
    total_spatial_time = 0.0
    
    window_name = "IBVAP M6 - Event Interpretation"
    if not no_show:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
    alert_log = []
    
    try:
        while pipeline.is_running:
            frame = pipeline.get_next_frame(timeout=0.1)
            
            if frame:
                # 1. AI Inference
                inf_start = time.perf_counter()
                detections = detector.detect(frame)
                inf_time = time.perf_counter() - inf_start
                total_inference_time += inf_time
                
                # 2. Tracking
                trk_start = time.perf_counter()
                tracks = tracker.update(detections, frame)
                trk_time = time.perf_counter() - trk_start
                total_tracker_time += trk_time
                metrics.record_tracker_latency(trk_time)
                
                # 3. Spatial Reasoning
                sp_start = time.perf_counter()
                spatial_events = spatial_engine.process(tracks, spatial_config)
                sp_time = time.perf_counter() - sp_start
                total_spatial_time += sp_time
                
                # 4. M6 Event Interpretation
                m6_alerts_before = m6_pipeline.metrics["alerts_created"]
                if spatial_events:
                    m6_pipeline.enqueue(spatial_events)
                    m6_pipeline.process_all_pending(current_frame=frame.data, current_tracks=tracks)
                
                # We check DB for new alerts to show on screen
                m6_alerts_after = m6_pipeline.metrics["alerts_created"]
                
                if not no_show and (m6_alerts_after > m6_alerts_before):
                    # For visualization we just log something new happened
                    alert_log.insert(0, f"M6 Alert Generated! Total: {m6_alerts_after}")
                    if len(alert_log) > 5:
                        alert_log.pop()
                            
                frames_processed += 1
                
                if not no_show:
                    vis_img = frame.data.copy()
                    
                    # Draw Zones
                    for z in spatial_config.zones:
                        pts = np.array([[int(p.x), int(p.y)] for p in z.geometry], np.int32)
                        pts = pts.reshape((-1, 1, 2))
                        cv2.polylines(vis_img, [pts], isClosed=True, color=(255, 0, 255), thickness=3)
                        
                    # Draw Tracks
                    for t in tracks:
                        if t.state.value != "ACTIVE":
                            continue
                        left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                        cv2.rectangle(vis_img, (left, top), (right, bottom), (255, 0, 0), 2)
                        cv2.putText(vis_img, f"{t.track_id.split('-')[-1]}", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        
                    # Draw Alert Log
                    for i, log_msg in enumerate(alert_log):
                        cv2.putText(vis_img, log_msg, (50, 200 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                    # Performance Overlay
                    stats = metrics.get_summary()
                    avg_m6 = m6_pipeline.metrics["avg_event_processing_ms"]
                    stats_text = f"Src: {stats['source_fps']:.1f} FPS | M6 Avg: {avg_m6:.2f}ms"
                    cv2.putText(vis_img, stats_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                    cv2.imshow(window_name, vis_img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    
    pipeline.stop()
    evidence_service.stop()
    cv2.destroyAllWindows()
    
    print("\n--- Final M6 Event Engine Performance Report ---")
    for k, v in m6_pipeline.metrics.items():
        if isinstance(v, float):
            print(f"{k.ljust(30)}: {v:.3f}")
        else:
            print(f"{k.ljust(30)}: {v}")
            
    print("\nCheck 'm6_test.db' for persisted states.")
    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 6 Integration Validation")
    default_video = os.environ.get("IBVAP_TEST_VIDEO", r"C:\Users\Harshal\Downloads\videoplayback.mp4")
    parser.add_argument("--video", type=str, default=default_video, help="Path to video file")
    parser.add_argument("--size", type=int, default=1280, help="Inference resolution")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--no-show", action="store_true", help="Disable visualization window for benchmarking")
    
    args = parser.parse_args()
    run_m6_test(args.video, args.size, args.conf, args.no_show)
