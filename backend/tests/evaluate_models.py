import cv2
import time
import os
import torch
import numpy as np
import argparse
from typing import List, Dict

# Set environment to run locally
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.perception.yolo_detector import YOLODetector
from app.domain.frame import Frame
from datetime import datetime, timezone

def evaluate_models(video_path: str, models: List[str], conf_thresh: float, inference_size: int):
    # Determine split line for lanes (heuristic based on 1280x720 video)
    # We will assume x < 640 is one lane and x >= 640 is the other.
    LANE_SPLIT_X = 640
    
    results = {}
    
    # representative frames to visualize
    rep_frames = [30, 60, 90]
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "model_eval")
    os.makedirs(output_dir, exist_ok=True)

    for model_name in models:
        print(f"\n{'='*50}")
        print(f"Evaluating Model: {model_name}")
        print(f"{'='*50}")
        
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        
        # Measure load time
        load_start = time.perf_counter()
        detector = YOLODetector(
            model_path=model_name,
            confidence_threshold=conf_thresh,
            inference_size=inference_size,
            device="cuda"
        )
        load_time = time.perf_counter() - load_start
        
        # Memory usage
        mem_allocated = torch.cuda.max_memory_allocated() / (1024 ** 2) # MB
        
        # Process Video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Failed to open video: {video_path}")
            continue
            
        frame_count = 0
        latencies = []
        
        # Stats
        total_detections = 0
        lane_left_count = 0
        lane_right_count = 0
        lane_left_confs = []
        lane_right_confs = []
        
        while frame_count < 150: # Evaluate 150 frames
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            # Wrap in Frame object
            dt = datetime.now(timezone.utc)
            f_obj = Frame(frame_id=str(frame_count), camera_id="eval_cam", timestamp=dt, width=frame.shape[1], height=frame.shape[0], data=frame)
            
            # Detect
            infer_start = time.perf_counter()
            detections = detector.detect(f_obj)
            latencies.append(time.perf_counter() - infer_start)
            
            total_detections += len(detections)
            
            for d in detections:
                cx = (d.bbox_xyxy[0] + d.bbox_xyxy[2]) / 2.0
                if cx < LANE_SPLIT_X:
                    lane_left_count += 1
                    lane_left_confs.append(d.confidence)
                else:
                    lane_right_count += 1
                    lane_right_confs.append(d.confidence)
            
            # Save visual for representative frames
            if frame_count in rep_frames:
                vis_img = frame.copy()
                for d in detections:
                    left, top, right, bottom = map(int, d.bbox_xyxy)
                    color = (0, 0, 255) if ((left+right)/2 < LANE_SPLIT_X) else (255, 0, 0) # Red left, Blue right
                    cv2.rectangle(vis_img, (left, top), (right, bottom), color, 2)
                    label = f"{d.class_name} {d.confidence:.2f}"
                    cv2.putText(vis_img, label, (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                # Draw split line
                cv2.line(vis_img, (LANE_SPLIT_X, 0), (LANE_SPLIT_X, frame.shape[0]), (0, 255, 255), 2)
                
                out_path = os.path.join(output_dir, f"{model_name.split('.')[0]}_frame_{frame_count}.jpg")
                cv2.imwrite(out_path, vis_img)
                
        cap.release()
        
        # Aggregate results
        avg_latency = np.mean(latencies) * 1000 # ms
        fps = 1000.0 / avg_latency if avg_latency > 0 else 0
        
        avg_conf_left = np.mean(lane_left_confs) if lane_left_confs else 0
        avg_conf_right = np.mean(lane_right_confs) if lane_right_confs else 0
        
        results[model_name] = {
            "load_time_s": load_time,
            "vram_mb": mem_allocated,
            "avg_latency_ms": avg_latency,
            "fps": fps,
            "total_detections": total_detections,
            "lane_left_count": lane_left_count,
            "lane_right_count": lane_right_count,
            "avg_conf_left": avg_conf_left,
            "avg_conf_right": avg_conf_right,
            "frames_processed": frame_count
        }
        
        print(f"Results for {model_name}:")
        for k, v in results[model_name].items():
            if isinstance(v, float):
                print(f"  {k}: {v:.2f}")
            else:
                print(f"  {k}: {v}")
                
if __name__ == "__main__":
    video = r"C:\Users\Harshal\Downloads\Traffic on Highway in City l Free Stock Footage _ No Copyright Videos _ Creative Common !.mp4"
    evaluate_models(video, ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"], 0.25, 1280)
