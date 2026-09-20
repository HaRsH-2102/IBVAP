import sys
import time
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker

def run_clean_benchmark(video_path: str, run_m5: bool):
    camera_id = "cam_test"
    metrics = StreamMetrics(window_size=30)
    stream_manager = FileStreamManager(camera_id, video_path)
    detector = YOLODetector(model_path="yolov8n.pt", confidence_threshold=0.25, inference_size=1280, device="auto")
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    
    if run_m5:
        from app.spatial.spatial_engine import SpatialEngine
        from tests.run_spatial import create_synthetic_config
        spatial_engine = SpatialEngine(crossing_epsilon=3.0)
        spatial_config = create_synthetic_config(camera_id)

    pipeline = CameraPipeline(stream_manager, metrics)
    pipeline.start()
    
    time.sleep(1.0)
    while True:
        f = pipeline.get_next_frame(timeout=0.0)
        if f is None:
            break
            
    metrics.reset()
    
    frames_processed = 0
    t_inf = 0.0
    t_trk = 0.0
    t_spa = 0.0
    
    while pipeline.is_running:
        frame = pipeline.get_next_frame(timeout=0.1)
        if frame:
            s1 = time.perf_counter()
            detections = detector.detect(frame)
            e1 = time.perf_counter()
            t_inf += (e1 - s1)
            
            s2 = time.perf_counter()
            tracks = tracker.update(detections, frame)
            e2 = time.perf_counter()
            t_trk += (e2 - s2)
            metrics.record_tracker_latency(e2 - s2)
            
            if run_m5:
                s3 = time.perf_counter()
                events = spatial_engine.process(tracks, spatial_config)
                e3 = time.perf_counter()
                t_spa += (e3 - s3)
                
            frames_processed += 1
            
    pipeline.stop()
    stats = metrics.get_summary()
    return {
        "frames": frames_processed,
        "dropped": stats["total_dropped"],
        "avg_inf": (t_inf / max(1, frames_processed)) * 1000,
        "avg_trk": (t_trk / max(1, frames_processed)) * 1000,
        "avg_spa": (t_spa / max(1, frames_processed)) * 1000 if run_m5 else 0.0,
        "end_to_end_fps": stats["processed_fps"]
    }

if __name__ == "__main__":
    video = os.environ.get("IBVAP_TEST_VIDEO", r"C:\Users\Harshal\Downloads\videoplayback.mp4")
    print("Running M4 Baseline...")
    res_m4 = run_clean_benchmark(video, False)
    print("M4 Baseline:", res_m4)
    
    print("\nRunning M5 Baseline...")
    res_m5 = run_clean_benchmark(video, True)
    print("M5 Baseline:", res_m5)
