"""
IBVAP — Milestone 7 Integration Validation
==========================================
Runs the complete M1->M7 pipeline on a video file.
Includes YOLO (M3), ByteTrack (M4), Spatial (M5), Event Interpretation (M6), and Behavioral Intelligence (M7).
"""

import sys
import time
import argparse
import os
import cv2
import numpy as np
from datetime import datetime

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
from app.event.pipeline import M6EventPipeline

from app.behavioral.config import BehavioralConfig
from app.behavioral.engine import BehavioralEngine
from app.behavioral.detectors import (
    LoiteringDetector, StationaryDetector, RestrictedZoneDwellDetector,
    RepeatedZoneEntryDetector, BoundaryApproachDetector, DirectionDetector
)

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

def create_highway_config(camera_id: str) -> CameraSpatialConfig:
    zone1 = Zone(
        zone_id="highway_zone",
        camera_id=camera_id,
        name="Highway Restricted",
        zone_type=ZoneType.RESTRICTED,
        geometry=[
            Point(x=200, y=400),
            Point(x=1080, y=400),
            Point(x=1280, y=700),
            Point(x=0, y=700)
        ]
    )
    
    line1 = VirtualLine(
        line_id="highway_line",
        camera_id=camera_id,
        name="Speed Check Line",
        start=Point(x=0, y=550),
        end=Point(x=1280, y=550),
        allowed_direction=Direction.BOTH
    )
    
    return CameraSpatialConfig(
        camera_id=camera_id,
        zones=[zone1],
        tripwires=[line1]
    )

def run_m7_test(video_path: str, inference_size: int, conf_thresh: float, no_show: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"Starting M7 Full Pipeline Validation:")
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
    
    if "Highway" in video_path:
        spatial_config = create_highway_config(camera_id)
    else:
        spatial_config = create_synthetic_config(camera_id)

    # Initialize M6
    if os.path.exists("m7_test.db"):
        os.remove("m7_test.db") # Start fresh for deterministic counts
    db = SQLiteDatabase("m7_test.db")
    sec_repo = SecurityEventRepository(db)
    alert_repo = AlertRepository(db)
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "m6_rules.yaml")
    rules = load_rules(config_path)
    rule_engine = RuleEngine(rules)
    correlator = BasicCorrelator(rules)
    alert_manager = AlertManager(alert_repo)
    
    m6_pipeline = M6EventPipeline(rule_engine, correlator, alert_manager, sec_repo)

    # Initialize M7
    m7_config = BehavioralConfig()
    # Speed up demonstration thresholds so we see events on a short video clip
    m7_config.loitering_duration = 2.0 
    m7_config.stationary_duration = 2.0
    m7_config.restricted_zone_dwell_duration = 2.0
    m7_config.repeated_zone_entry_count = 2
    
    m7_engine = BehavioralEngine(
        config=m7_config,
        detectors=[
            LoiteringDetector(),
            StationaryDetector(),
            RestrictedZoneDwellDetector(),
            RepeatedZoneEntryDetector(),
            BoundaryApproachDetector(),
            DirectionDetector()
        ]
    )

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
    total_m7_time = 0.0
    
    window_name = "IBVAP M7 - Behavioral Intelligence"
    if not no_show:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
    alert_log = []
    
    try:
        while pipeline.is_running:
            frame = pipeline.get_next_frame(timeout=0.1)
            
            if frame:
                current_time = datetime.now() # Mock wall-clock timestamp since FileStreamManager doesn't embed true video PTS in this prototype
                
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
                
                # 4. Behavioral Reasoning (M7)
                m7_start = time.perf_counter()
                behavioral_events = m7_engine.process(tracks, spatial_events, current_time)
                m7_time = time.perf_counter() - m7_start
                total_m7_time += m7_time
                
                # 5. M6 Event Interpretation
                m6_alerts_before = m6_pipeline.metrics["alerts_created"]
                
                # Enqueue both spatial and behavioral events to M6
                all_events = []
                all_events.extend(spatial_events)
                all_events.extend(behavioral_events)
                
                if all_events:
                    m6_pipeline.enqueue(all_events)
                    m6_pipeline.process_all_pending()
                
                m6_alerts_after = m6_pipeline.metrics["alerts_created"]
                
                if not no_show and (m6_alerts_after > m6_alerts_before):
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
                        
                        # Find if there's an active behavior for this track to highlight it
                        state_key = (t.camera_id, t.track_id)
                        color = (255, 0, 0)
                        behavior_txt = ""
                        if state_key in m7_engine.track_states:
                            t_state = m7_engine.track_states[state_key]
                            for b_type, info in t_state.active_behaviors.items():
                                if info.get("status") in ["LOITERING", "STATIONARY"]:
                                    color = (0, 0, 255) # Red for suspicious behavior
                                    behavior_txt = b_type
                                    break
                                    
                        cv2.rectangle(vis_img, (left, top), (right, bottom), color, 2)
                        label = f"{t.track_id.split('-')[-1]} {behavior_txt}"
                        cv2.putText(vis_img, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
                    # Draw Alert Log
                    for i, log_msg in enumerate(alert_log):
                        cv2.putText(vis_img, log_msg, (50, 200 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                    # Performance Overlay
                    stats = metrics.get_summary()
                    avg_m7 = (total_m7_time / frames_processed) * 1000
                    stats_text = f"Src: {stats['source_fps']:.1f} FPS | M7 Avg: {avg_m7:.2f}ms"
                    cv2.putText(vis_img, stats_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                    cv2.imshow(window_name, vis_img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    
    pipeline.stop()
    cv2.destroyAllWindows()
    
    print("\n--- Final M7 Behavioral Engine Performance Report ---")
    avg_m7 = (total_m7_time / max(1, frames_processed)) * 1000
    print(f"Frames processed: {frames_processed}")
    print(f"M7 Avg latency per frame: {avg_m7:.3f} ms")
    
    # Let's count emitted behaviors by peeking into the M6 metrics or tracking them locally
    # M6 metrics tracks "security_events_generated"
    for k, v in m6_pipeline.metrics.items():
        if isinstance(v, float):
            print(f"M6 {k.ljust(27)}: {v:.3f}")
        else:
            print(f"M6 {k.ljust(27)}: {v}")
            
    print("\nCheck 'm7_test.db' for persisted M6 events based on M7 behaviors.")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 7 Integration Validation")
    default_video = os.environ.get("IBVAP_TEST_VIDEO", r"C:\Users\Harshal\Downloads\videoplayback.mp4")
    parser.add_argument("--video", type=str, default=default_video, help="Path to video file")
    parser.add_argument("--size", type=int, default=1280, help="Inference resolution")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--no-show", action="store_true", help="Disable visualization window for benchmarking")
    
    args = parser.parse_args()
    run_m7_test(args.video, args.size, args.conf, args.no_show)
