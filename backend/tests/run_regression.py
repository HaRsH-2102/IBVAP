import sys
import time
import argparse
import os
import cv2
import numpy as np
from datetime import datetime
from collections import defaultdict

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
from app.night.config import NightConfig
from app.night.engine import NightEngine
from app.domain.night import SceneState

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

def run_regression(video_path: str, model_name: str) -> None:
    print(f"Starting Detailed Regression: {model_name}")
    
    settings.playback_mode = "real_time"
    camera_id = "reg_cam_01"
    
    metrics = StreamMetrics(window_size=30)
    stream_manager = FileStreamManager(camera_id, video_path)
    
    detector = YOLODetector(
        model_path=model_name,
        confidence_threshold=0.25,
        inference_size=1280,
        device="cuda" 
    )
    
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    spatial_engine = SpatialEngine(crossing_epsilon=3.0)
    spatial_config = create_highway_config(camera_id)

    if os.path.exists("reg_test.db"):
        os.remove("reg_test.db")
    db = SQLiteDatabase("reg_test.db")
    sec_repo = SecurityEventRepository(db)
    alert_repo = AlertRepository(db)
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "m6_rules.yaml")
    rules = load_rules(config_path)
    rule_engine = RuleEngine(rules)
    correlator = BasicCorrelator(rules)
    alert_manager = AlertManager(alert_repo)
    m6_pipeline = M6EventPipeline(rule_engine, correlator, alert_manager, sec_repo)

    m7_config = BehavioralConfig()
    m7_engine = BehavioralEngine(
        config=m7_config,
        detectors=[LoiteringDetector(), StationaryDetector(), RestrictedZoneDwellDetector(), RepeatedZoneEntryDetector(), BoundaryApproachDetector(), DirectionDetector()]
    )
    
    m8_config = NightConfig()
    m8_engine = NightEngine(config=m8_config)

    pipeline = CameraPipeline(stream_manager, metrics)
    pipeline.start()
    
    # Detailed Metrics
    stats = {
        "m3_total": 0, "m3_oncoming": 0, "m3_outgoing": 0,
        "m4_max_simultaneous": 0, "m4_total_unique_ids": set(),
        "m5_zone_enter": 0, "m5_zone_exit": 0, "m5_line_cross": 0,
        "m7_events": defaultdict(int),
        "latencies": defaultdict(list)
    }
    
    LANE_SPLIT_X = 640
    rep_frames = [50, 100, 150]
    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")
    
    frames_processed = 0
    start_time = time.perf_counter()
    
    try:
        while pipeline.is_running and frames_processed < 250:
            frame = pipeline.get_next_frame(timeout=0.1)
            if not frame:
                continue
                
            current_time = datetime.now()
            
            # M3
            t0 = time.perf_counter()
            detections = detector.detect(frame)
            stats["latencies"]["m3"].append(time.perf_counter() - t0)
            stats["m3_total"] += len(detections)
            for d in detections:
                cx = (d.bbox_xyxy[0] + d.bbox_xyxy[2]) / 2.0
                if cx >= LANE_SPLIT_X:
                    stats["m3_oncoming"] += 1
                else:
                    stats["m3_outgoing"] += 1
            
            # M4
            t0 = time.perf_counter()
            tracks = tracker.update(detections, frame)
            stats["latencies"]["m4"].append(time.perf_counter() - t0)
            
            active_tracks = [t for t in tracks if t.state.value == "ACTIVE"]
            stats["m4_max_simultaneous"] = max(stats["m4_max_simultaneous"], len(active_tracks))
            for t in tracks:
                stats["m4_total_unique_ids"].add(t.track_id)
                
            # M5
            t0 = time.perf_counter()
            sp_events = spatial_engine.process(tracks, spatial_config)
            stats["latencies"]["m5"].append(time.perf_counter() - t0)
            
            for e in sp_events:
                if e.event_type.value == "ZONE_ENTER": stats["m5_zone_enter"] += 1
                elif e.event_type.value == "ZONE_EXIT": stats["m5_zone_exit"] += 1
                elif e.event_type.value == "LINE_CROSS": stats["m5_line_cross"] += 1
                
            # M7
            t0 = time.perf_counter()
            beh_events = m7_engine.process(tracks, sp_events, current_time)
            stats["latencies"]["m7"].append(time.perf_counter() - t0)
            for e in beh_events:
                stats["m7_events"][e.behavior_type] += 1
                
            # M8
            t0 = time.perf_counter()
            scene_state, night_events = m8_engine.process(camera_id, frame.data, tracks, beh_events, current_time)
            stats["latencies"]["m8"].append(time.perf_counter() - t0)
            
            # Feedback scene state to M3 for adaptive profile
            detector.set_scene_state(scene_state)
            
            # M6
            all_events = sp_events + beh_events + night_events
            if all_events:
                m6_pipeline.enqueue(all_events)
                m6_pipeline.process_all_pending()
                
            frames_processed += 1
            
            if frames_processed in rep_frames:
                vis = frame.data.copy()
                for t in active_tracks:
                    left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                    cx = (left + right) / 2
                    color = (255, 0, 0) if cx >= LANE_SPLIT_X else (0, 0, 255) # Blue oncoming, Red outgoing
                    cv2.rectangle(vis, (left, top), (right, bottom), color, 2)
                    cv2.putText(vis, f"ID:{t.track_id.split('-')[-1]}", (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                cv2.line(vis, (LANE_SPLIT_X, 0), (LANE_SPLIT_X, 720), (0, 255, 255), 2)
                cv2.imwrite(os.path.join(out_dir, f"regression_frame_{frames_processed}.jpg"), vis)
                
    finally:
        pipeline.stop()
        
    print("\n--- Regression Results ---")
    print(f"M3 Total Dets: {stats['m3_total']} (Oncoming: {stats['m3_oncoming']}, Outgoing: {stats['m3_outgoing']})")
    print(f"M4 Max Simultaneous Tracks: {stats['m4_max_simultaneous']}")
    print(f"M4 Unique Track IDs: {len(stats['m4_total_unique_ids'])}")
    print(f"M5 Events: ENTER={stats['m5_zone_enter']}, EXIT={stats['m5_zone_exit']}, CROSS={stats['m5_line_cross']}")
    print(f"M6 Alerts Created: {m6_pipeline.metrics['alerts_created']}")
    print(f"M7 Events: {dict(stats['m7_events'])}")
    print(f"M8 Final Scene State: {scene_state.name}")
    print(f"Final M3 Confidence: {detector.conf:.2f}")
    
    for mod in ["m3", "m4", "m5", "m7", "m8"]:
        arr = stats["latencies"][mod]
        avg = (sum(arr) / len(arr)) * 1000 if arr else 0
        print(f"Latency {mod.upper()}: {avg:.2f} ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--model", type=str, default="yolov8s.pt")
    args = parser.parse_args()
    run_regression(args.video, args.model)
