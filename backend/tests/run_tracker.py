"""
IBVAP — Milestone 4 Technical Validation
========================================
Runs the Object Tracker against a local video file to validate:
- Multi-Object Tracking logic (ByteTrack)
- Track lifecycle (NEW, ACTIVE, LOST, REMOVED)
- Object ID persistence across frames
- Track trajectory visualization
- Tracker latency separate from AI latency
"""

import sys
import time
import argparse
import os
import cv2

# Ensure backend root is in Python path when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.config import settings
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker

# Milestone 4 canonical video
SAMPLE_VIDEO_PATH = r"C:\Users\Harshal\Downloads\videoplayback.mp4"


def run_tracker_test(video_path: str, inference_size: int, conf_thresh: float, no_show: bool = False) -> None:
    """
    Run the multi-object tracking pipeline validation test.
    """
    print(f"\n{'='*60}")
    print(f"Starting M4 Tracking Validation:")
    print(f"Video: {video_path}")
    print(f"Size : {inference_size}x{inference_size}")
    print(f"Conf : {conf_thresh}")
    print(f"{'='*60}")
    
    settings.playback_mode = "real_time"
    
    # 1. Initialize dependencies
    metrics = StreamMetrics(window_size=30)
    
    try:
        stream_manager = FileStreamManager("cam_test_01", video_path)
    except Exception as e:
        print(f"Failed to open video file: {e}")
        return
    
    # 2. Initialize detector
    try:
        detector = YOLODetector(
            model_path="yolov8n.pt",
            confidence_threshold=conf_thresh,
            inference_size=inference_size,
            device="auto" 
        )
    except Exception as e:
        print(f"Detector initialization failed: {e}")
        return
        
    # 3. Initialize tracker
    tracker = ByteTrackTracker(camera_id="cam_test_01", track_buffer=30)

    # 4. Initialize pipeline
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
    
    window_name = "IBVAP M4 - MOT Validation (ByteTrack)"
    if not no_show:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    try:
        while pipeline.is_running:
            frame = pipeline.get_next_frame(timeout=0.1)
            
            if frame:
                # --- 1. Detection Phase ---
                inf_start = time.perf_counter()
                detections = detector.detect(frame)
                inf_time = time.perf_counter() - inf_start
                total_inference_time += inf_time
                
                # --- 2. Tracking Phase ---
                trk_start = time.perf_counter()
                tracks = tracker.update(detections, frame)
                trk_time = time.perf_counter() - trk_start
                total_tracker_time += trk_time
                metrics.record_tracker_latency(trk_time)
                
                # Update metrics track count
                active_count = len([t for t in tracks if t.state.value == "ACTIVE"])
                metrics.set_active_tracks(active_count)
                
                frames_processed += 1
                
                # --- 3. Visualization ---
                vis_img = frame.data.copy()
                
                for t in tracks:
                    if t.state.value != "ACTIVE":
                        continue
                        
                    left = int(t.bounding_box.left)
                    top = int(t.bounding_box.top)
                    right = int(t.bounding_box.right)
                    bottom = int(t.bounding_box.bottom)
                    
                    # Generate a consistent color based on track ID
                    # We hash the track string to an int
                    h = hash(t.track_id)
                    color = ((h * 131) % 255, (h * 179) % 255, (h * 211) % 255)
                    
                    cv2.rectangle(vis_img, (left, top), (right, bottom), color, 2)
                    
                    # Draw label: ID and Class
                    label = f"ID:{t.track_id.split('-')[-1]} {t.object_class.name}"
                    cv2.putText(vis_img, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    # Draw trajectory trailing lines
                    if len(t.trajectory) > 1:
                        pts = []
                        # Take last 30 points for the tail
                        for point in t.trajectory[-30:]:
                            cx = int((point.bounding_box.left + point.bounding_box.right) / 2)
                            cy = int((point.bounding_box.top + point.bounding_box.bottom) / 2)
                            pts.append((cx, cy))
                            
                        for i in range(1, len(pts)):
                            cv2.line(vis_img, pts[i - 1], pts[i], color, 2)

                # Overlay performance stats on the image
                avg_inf_ms = (total_inference_time / frames_processed) * 1000
                avg_trk_ms = (total_tracker_time / frames_processed) * 1000
                stats = metrics.get_summary()
                
                stats_text = (
                    f"Src: {stats['source_fps']:.1f} FPS | "
                    f"E2E Latency: {stats['avg_latency_ms']:.1f}ms | "
                    f"Inf: {avg_inf_ms:.1f}ms | "
                    f"Trk: {avg_trk_ms:.1f}ms | "
                    f"Active: {stats['active_tracks']}"
                )
                cv2.putText(vis_img, stats_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                if not no_show:
                    cv2.imshow(window_name, vis_img)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    
    # Stop and Report
    pipeline.stop()
    cv2.destroyAllWindows()
    
    print("\n--- Final M4 Tracking Performance Report ---")
    final_stats = metrics.get_summary()
    
    avg_inf_ms = (total_inference_time / max(1, frames_processed)) * 1000
    avg_trk_ms = (total_tracker_time / max(1, frames_processed)) * 1000
    
    print("M3 - RAW AI INFERENCE:")
    print(f"{'avg_inference_ms'.ljust(20)}: {avg_inf_ms:.2f} ms")
    
    print("\nM4 - TRACKER OVERHEAD:")
    print(f"{'avg_tracker_ms'.ljust(20)}: {avg_trk_ms:.2f} ms")
    
    print("\nM2/M3/M4 - PIPELINE END-TO-END:")
    for key, value in final_stats.items():
        if isinstance(value, float):
            print(f"{key.ljust(20)}: {value:.2f}")
        else:
            print(f"{key.ljust(20)}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 4 Tracking Validation")
    parser.add_argument("--video", type=str, default=SAMPLE_VIDEO_PATH, help="Path to video file")
    parser.add_argument("--size", type=int, default=1280, help="Inference resolution")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--no-show", action="store_true", help="Disable visualization window for benchmarking")
    
    args = parser.parse_args()

    run_tracker_test(args.video, args.size, args.conf, args.no_show)
