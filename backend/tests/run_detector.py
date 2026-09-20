"""
IBVAP — Milestone 3 Technical Validation
========================================
Runs the Object Detector against a local video file to validate:
- YOLO model loading and warmup
- Conversion of model outputs to IBVAP Detection objects
- Inference latency vs End-to-End latency separation
- Bounding box extraction and visualization
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

# Milestone 2 canonical video
SAMPLE_VIDEO_PATH = r"E:\CSMSS Projects\Sem6_mini_project\FaceForensics++_C23\Face2Face\013_883.mp4"


def run_detector_test(video_path: str, inference_size: int, conf_thresh: float, no_show: bool = False) -> None:
    """
    Run the object detection pipeline validation test.
    """
    print(f"\n{'='*60}")
    print(f"Starting M3 Validation:")
    print(f"Video: {video_path}")
    print(f"Size : {inference_size}x{inference_size}")
    print(f"Conf : {conf_thresh}")
    print(f"{'='*60}")
    
    # Configure for benchmark (unpaced) to see max hardware limits, or paced for realism.
    # We use 'max_throughput' to truly stress the AI layer if the video is short, 
    # but for visualization, 'real_time' is better. We'll use real_time for visual tests.
    settings.playback_mode = "real_time"
    
    # 1. Initialize dependencies
    metrics = StreamMetrics(window_size=30)
    
    try:
        stream_manager = FileStreamManager("cam_test_01", video_path)
    except Exception as e:
        print(f"Failed to open video file: {e}")
        return
    
    # 2. Initialize detector (This downloads weights and warms up)
    try:
        detector = YOLODetector(
            model_path="yolov8n.pt",
            confidence_threshold=conf_thresh,
            inference_size=inference_size,
            device="auto"  # Automatically picks GPU if available
        )
    except Exception as e:
        print(f"Detector initialization failed: {e}")
        return

    # 3. Initialize pipeline
    pipeline = CameraPipeline(stream_manager, metrics)
    pipeline.start()
    
    # Give the capture thread a moment to buffer the first frames
    print("Waiting for capture thread to warm up...")
    time.sleep(1.0)
    
    # Drain any frames that accumulated during warmup so we start fresh
    print("Draining warmup frames...")
    while True:
        f = pipeline.get_next_frame(timeout=0.0)
        if f is None:
            break
            
    # Reset metrics so the benchmark measurement is perfectly clean
    metrics.reset()
    
    frames_processed = 0
    total_inference_time = 0.0
    
    window_name = "IBVAP M3 - Object Detection Validation"
    if not no_show:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    try:
        while pipeline.is_running:
            # End-to-end start time is when the consumer loop asks for a frame
            e2e_start = time.perf_counter()
            
            # Pull frame from pipeline
            frame = pipeline.get_next_frame(timeout=0.1)
            
            if frame:
                # Inference start time
                inf_start = time.perf_counter()
                
                # Perform AI Detection
                detections = detector.detect(frame)
                
                inf_time = time.perf_counter() - inf_start
                total_inference_time += inf_time
                frames_processed += 1
                
                # --- Visualization ---
                # We need a mutable copy of the image to draw on
                vis_img = frame.data.copy()
                
                for det in detections:
                    left, top, right, bottom = map(int, det.bbox_xyxy)
                    
                    # Draw bounding box
                    color = (0, 255, 0) # Green
                    cv2.rectangle(vis_img, (left, top), (right, bottom), color, 2)
                    
                    # Draw label and confidence
                    label = f"{det.class_name} {det.confidence:.2f}"
                    cv2.putText(vis_img, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Overlay performance stats on the image
                avg_inf_ms = (total_inference_time / frames_processed) * 1000
                stats = metrics.get_summary()
                stats_text = (
                    f"Src FPS: {stats['source_fps']:.1f} | "
                    f"E2E Latency: {stats['avg_latency_ms']:.1f}ms | "
                    f"Inf: {avg_inf_ms:.1f}ms"
                )
                cv2.putText(vis_img, stats_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                # Show image
                if not no_show:
                    cv2.imshow(window_name, vis_img)
                    
                    # Press 'q' to quit early
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    
    # 4. Stop and Report
    pipeline.stop()
    cv2.destroyAllWindows()
    
    print("\n--- Final M3 Performance Report ---")
    final_stats = metrics.get_summary()
    
    avg_inf_ms = (total_inference_time / max(1, frames_processed)) * 1000
    inf_fps = 1000.0 / avg_inf_ms if avg_inf_ms > 0 else 0
    
    print("M3 - RAW AI INFERENCE:")
    print(f"{'avg_inference_ms'.ljust(20)}: {avg_inf_ms:.2f} ms")
    print(f"{'inference_fps'.ljust(20)}: {inf_fps:.2f} FPS")
    print()
    print("M2/M3 - PIPELINE END-TO-END:")
    for key, value in final_stats.items():
        if isinstance(value, float):
            print(f"{key.ljust(20)}: {value:.2f}")
        else:
            print(f"{key.ljust(20)}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 3 Detection Validation")
    parser.add_argument("--video", type=str, default=SAMPLE_VIDEO_PATH, help="Path to video file")
    parser.add_argument("--size", type=int, default=640, help="Inference resolution")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--no-show", action="store_true", help="Disable visualization window for benchmarking")
    
    args = parser.parse_args()

    run_detector_test(args.video, args.size, args.conf, args.no_show)
