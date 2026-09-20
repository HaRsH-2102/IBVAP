import sys
import time
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
            Point(x=10, y=10),
            Point(x=3000, y=10),
            Point(x=3000, y=2000),
            Point(x=10, y=2000)
        ]
    )
    return CameraSpatialConfig(camera_id=camera_id, zones=[zone1], tripwires=[])

def run_test():
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "tests", "assets", "videoplayback.mp4"))
    camera_id = "cam_test_01"
    
    metrics = StreamMetrics(window_size=30)
    
    stream_manager = FileStreamManager(camera_id, video_path)
        
    detector = YOLODetector(
        model_path="rtdetr-l.pt",
        confidence_threshold=0.65,
        device="auto" 
    )
    
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    spatial_engine = SpatialEngine(crossing_epsilon=3.0)
    spatial_config = create_synthetic_config(camera_id)

    db = SQLiteDatabase()
    sec_repo = SecurityEventRepository(db)
    alert_repo = AlertRepository(db)
    
    config_path = os.path.join(os.path.dirname(__file__), "config", "m6_rules.yaml")
        
    rules = load_rules(config_path)
    rule_engine = RuleEngine(rules)
    correlator = BasicCorrelator(rules)
    alert_manager = AlertManager(alert_repo)
    
    m6_pipeline = M6EventPipeline(rule_engine, correlator, alert_manager, sec_repo)

    m7_config = BehavioralConfig()
    m7_config.loitering_duration = 2.0 
    m7_config.stationary_duration = 2.0
    
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
    
    print("Draining warmup frames...")
    while True:
        f = pipeline.get_next_frame(timeout=0.0)
        if f is None: break
            
    try:
        while pipeline.is_running:
            frame = pipeline.get_next_frame(timeout=0.1)
            
            if frame:
                current_time = datetime.utcnow()
                detections = detector.detect(frame)
                tracks = tracker.update(detections, frame)
                spatial_events = spatial_engine.process(tracks, spatial_config)
                behavioral_events = m7_engine.process(tracks, spatial_events, current_time)
                
                all_events = []
                all_events.extend(spatial_events)
                all_events.extend(behavioral_events)
                
                if all_events:
                    m6_pipeline.enqueue(all_events)
                    m6_pipeline.process_all_pending()
                        
    except KeyboardInterrupt:
        pass
    
    pipeline.stop()
    print("Generated Alerts:", m6_pipeline.metrics["alerts_created"])
    print("Check db for events.")

if __name__ == "__main__":
    run_test()
