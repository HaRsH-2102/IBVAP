import time
import argparse
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ingestion.opencv_stream import FileStreamManager
from app.perception.yolo_detector import YOLODetector
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline

def eval_m2_m3(video_path: str, model_name: str, conf_thresh: float):
    print(f"Evaluating Pipeline (M2+M3) with {model_name}")
    
    # Initialize M3
    detector = YOLODetector(
        model_path=model_name,
        confidence_threshold=conf_thresh,
        inference_size=1280,
        device="cuda"
    )
    
    metrics = StreamMetrics()
    stream_manager = FileStreamManager("eval_cam", video_path)
    # Using max_throughput to measure absolute maximum performance
    pipeline = CameraPipeline(stream_manager, metrics, playback_mode="max_throughput")
    
    pipeline.start()
    
    start_time = time.perf_counter()
    frames_processed = 0
    detector_latencies = []
    e2e_latencies = []
    
    try:
        while True:
            frame = pipeline.get_next_frame(timeout=2.0)
            if not frame:
                if not pipeline.is_running:
                    break
                continue
                
            e2e_start = time.perf_counter()
            
            # Detect
            det_start = time.perf_counter()
            detections = detector.detect(frame)
            det_latency = time.perf_counter() - det_start
            
            e2e_latency = time.perf_counter() - e2e_start
            
            detector_latencies.append(det_latency)
            e2e_latencies.append(e2e_latency)
            frames_processed += 1
            
            if frames_processed >= 300: # Evaluate 300 frames
                break
                
    finally:
        pipeline.stop()
        
    total_time = time.perf_counter() - start_time
    
    print("\n--- Pipeline Metrics ---")
    print(f"Source FPS: {metrics.source_fps:.2f}")
    print(f"Frames Received: {metrics.total_received}")
    print(f"Frames Processed: {metrics.total_processed}")
    print(f"Frames Dropped: {metrics.total_dropped}")
    
    avg_det_ms = (sum(detector_latencies) / len(detector_latencies)) * 1000 if detector_latencies else 0
    avg_e2e_ms = (sum(e2e_latencies) / len(e2e_latencies)) * 1000 if e2e_latencies else 0
    
    print(f"Processed FPS: {frames_processed / total_time:.2f}")
    print(f"Avg Detector Latency: {avg_det_ms:.2f} ms")
    print(f"Avg E2E Pipeline Latency (M2+M3): {avg_e2e_ms:.2f} ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--model", type=str, default="yolov8s.pt")
    args = parser.parse_args()
    eval_m2_m3(args.video, args.model, 0.25)
