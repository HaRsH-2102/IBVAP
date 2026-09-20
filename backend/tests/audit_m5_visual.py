import sys
import time
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.config import settings
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker
from app.domain.zone import Zone, Point, ZoneType
from app.domain.virtual_line import VirtualLine, Direction
from app.domain.spatial import CameraSpatialConfig
from app.spatial.spatial_engine import SpatialEngine

def create_synthetic_config(camera_id: str) -> CameraSpatialConfig:
    # A massive polygon zone covering most of the screen
    zone1 = Zone(
        zone_id="zone_01",
        camera_id=camera_id,
        name="Test Zone",
        zone_type=ZoneType.RESTRICTED,
        geometry=[
            Point(x=100, y=100),
            Point(x=1800, y=100),
            Point(x=1800, y=980),
            Point(x=100, y=980)
        ]
    )
    
    # A horizontal tripwire across the screen
    line1 = VirtualLine(
        line_id="line_01",
        camera_id=camera_id,
        name="Test Fence",
        start=Point(x=0, y=500),
        end=Point(x=1920, y=500),
        allowed_direction=Direction.BOTH
    )
    
    return CameraSpatialConfig(camera_id=camera_id, zones=[zone1], tripwires=[line1])

def run_visual_audit(video_path: str, out_img: str):
    settings.playback_mode = "real_time"
    camera_id = "cam_test"
    metrics = StreamMetrics(window_size=30)
    
    stream_manager = FileStreamManager(camera_id, video_path)
    detector = YOLODetector(model_path="yolov8s.pt", confidence_threshold=0.25, inference_size=1280, device="auto")
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    spatial_engine = SpatialEngine(crossing_epsilon=3.0)
    spatial_config = create_synthetic_config(camera_id)
    
    pipeline = CameraPipeline(stream_manager, metrics)
    pipeline.start()
    
    time.sleep(1.0)
    
    saved = False
    events_found = 0
    start_time = time.time()
    
    while pipeline.is_running and (time.time() - start_time) < 15.0:
        frame = pipeline.get_next_frame(timeout=0.1)
        if frame:
            detections = detector.detect(frame)
            tracks = tracker.update(detections, frame)
            events = spatial_engine.process(tracks, spatial_config)
            
            if len(events) > 0:
                events_found += len(events)
                
            if events_found > 0 and not saved:
                vis_img = frame.data.copy()
                for z in spatial_config.zones:
                    pts = np.array([[int(p.x), int(p.y)] for p in z.geometry], np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(vis_img, [pts], isClosed=True, color=(255, 0, 255), thickness=3)
                    cv2.putText(vis_img, z.name, (int(z.geometry[0].x), int(z.geometry[0].y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                    
                for l in spatial_config.tripwires:
                    cv2.line(vis_img, (int(l.start.x), int(l.start.y)), (int(l.end.x), int(l.end.y)), (0, 255, 255), 3)
                    cv2.putText(vis_img, l.name, (int(l.start.x), int(l.start.y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                for t in tracks:
                    if t.state.value != "ACTIVE": continue
                    left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                    cv2.rectangle(vis_img, (left, top), (right, bottom), (255, 0, 0), 2)
                    ref_x = int((left + right) / 2)
                    ref_y = bottom
                    cv2.circle(vis_img, (ref_x, ref_y), 5, (0, 0, 255), -1)
                
                for i, e in enumerate(events):
                    cv2.putText(vis_img, f"EVENT: {e.event_type.name} on {e.spatial_object_id}", (50, 50 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                cv2.imwrite(out_img, vis_img)
                print(f"Saved visual evidence to {out_img}")
                saved = True
                
    pipeline.stop()
    print(f"Total Spatial Events found: {events_found}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--out", type=str, required=True)
    args = parser.parse_args()
    run_visual_audit(args.video, args.out)
