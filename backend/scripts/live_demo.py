import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime, timezone

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
from app.behavioral.detectors.stationary import StationaryDetector
from app.behavioral.detectors.dwell import RestrictedZoneDwellDetector
from app.behavioral.detectors.repeated_entry import RepeatedZoneEntryDetector

from app.night.config import NightConfig, CameraNightConfig
from app.night.scene_analyzer import SceneAnalyzer

def create_synthetic_config(camera_id: str) -> CameraSpatialConfig:
    zone1 = Zone(
        zone_id="restricted_parking",
        camera_id=camera_id,
        name="Restricted Area",
        zone_type=ZoneType.RESTRICTED,
        geometry=[
            Point(x=100, y=100),
            Point(x=1800, y=100),
            Point(x=1800, y=980),
            Point(x=100, y=980)
        ]
    )
    
    line1 = VirtualLine(
        line_id="border_line",
        camera_id=camera_id,
        name="Security Fence",
        start=Point(x=0, y=500),
        end=Point(x=1920, y=500),
        allowed_direction=Direction.BOTH
    )
    
    return CameraSpatialConfig(camera_id=camera_id, zones=[zone1], tripwires=[line1])

def run_demo(video_path: str):
    print("Initializing IBVAP M1-M10 Pipeline Demo...")
    camera_id = "cam_live_01"
    
    # Core Config
    settings.playback_mode = "real_time"
    metrics = StreamMetrics(window_size=30)
    
    # 1. Ingestion
    stream_manager = FileStreamManager(camera_id, video_path)
    pipeline = CameraPipeline(stream_manager, metrics)
    
    # 2. Perception & Tracking
    detector = YOLODetector(model_path="yolov8s.pt", confidence_threshold=0.25, inference_size=640, device="auto")
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    
    # 3. Spatial
    spatial_config = create_synthetic_config(camera_id)
    spatial_engine = SpatialEngine()
    
    # 4. Behavioral
    b_config = BehavioralConfig(
        loitering_duration=5.0,
        stationary_duration=3.0,
        restricted_zone_dwell_duration=4.0
    )
    b_detectors = [LoiteringDetector(), StationaryDetector(), RestrictedZoneDwellDetector(), RepeatedZoneEntryDetector()]
    behavioral_engine = BehavioralEngine(b_config, b_detectors)
    
    # 5. Scene Analyzer
    n_config = NightConfig(camera_overrides={camera_id: CameraNightConfig()})
    scene_analyzer = SceneAnalyzer(n_config)
    
    pipeline.start()
    time.sleep(1.0)
    print("Pipeline Started. Opening visualization window...")
    
    cv2.namedWindow("IBVAP Live Demo - M1 to M10", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("IBVAP Live Demo - M1 to M10", 1280, 720)
    
    active_events = []
    
    try:
        while pipeline.is_running:
            frame = pipeline.get_next_frame(timeout=0.1)
            if frame:
                current_time = datetime.now(timezone.utc)
                vis_img = frame.data.copy()
                
                # --- AI Inference ---
                detections = detector.detect(frame)
                tracks = tracker.update(detections, frame)
                
                # --- Intelligence Engines ---
                scene_state, scene_metrics = scene_analyzer.analyze(camera_id, vis_img, current_time)
                spatial_events = spatial_engine.process(tracks, spatial_config)
                behavioral_events = behavioral_engine.process(tracks, spatial_events, current_time)
                
                # Update event logs for display
                for e in spatial_events:
                    active_events.insert(0, f"SPATIAL: {e.event_type.name} on {e.spatial_object_id} ({e.track_id})")
                for e in behavioral_events:
                    active_events.insert(0, f"BEHAVIOR: {e.behavior_type.name} ({e.track_id})")
                    
                active_events = active_events[:5] # Keep last 5
                
                # --- Rendering ---
                # Draw Zones
                for z in spatial_config.zones:
                    pts = np.array([[int(p.x), int(p.y)] for p in z.geometry], np.int32).reshape((-1, 1, 2))
                    cv2.polylines(vis_img, [pts], isClosed=True, color=(0, 100, 255), thickness=2)
                    cv2.putText(vis_img, z.name, (int(z.geometry[0].x), int(z.geometry[0].y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)
                    
                # Draw Lines
                for l in spatial_config.tripwires:
                    cv2.line(vis_img, (int(l.start.x), int(l.start.y)), (int(l.end.x), int(l.end.y)), (0, 255, 255), 2)
                    cv2.putText(vis_img, l.name, (int(l.start.x), int(l.start.y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Draw Tracks
                for t in tracks:
                    if t.state.value != "ACTIVE": continue
                    left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                    color = (0, 255, 0)
                    cv2.rectangle(vis_img, (left, top), (right, bottom), color, 2)
                    label = f"{t.object_class.name} {t.track_id}"
                    cv2.putText(vis_img, label, (left, max(20, top - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # HUD Overlays
                stats = metrics.get_summary()
                fps = stats['processed_fps']
                hud = [
                    f"IBVAP M1-M10 Live Demo",
                    f"FPS: {fps} | Latency: {stats['avg_latency_ms']}ms",
                    f"Scene: {scene_state.name} (Lux: {scene_metrics.get('median_luminance', 0):.1f})",
                    f"Active Tracks: {len([t for t in tracks if t.state.value == 'ACTIVE'])}"
                ]
                
                for i, text in enumerate(hud):
                    cv2.putText(vis_img, text, (20, 40 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    
                # Event log
                cv2.putText(vis_img, "RECENT EVENTS:", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                for i, text in enumerate(active_events):
                    cv2.putText(vis_img, text, (20, 230 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Display
                cv2.imshow("IBVAP Live Demo - M1 to M10", vis_img)
                
                # Press 'q' to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
        print("Demo finished.")

if __name__ == "__main__":
    video = "C:\\Users\\Harshal\\Downloads\\videoplayback.mp4"
    if len(sys.argv) > 1:
        video = sys.argv[1]
    run_demo(video)
