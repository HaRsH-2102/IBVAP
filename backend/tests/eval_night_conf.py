import sys
import os
import cv2
import time
import argparse
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.perception.yolo_detector import YOLODetector

def run_threshold_eval(video_path: str, model_path: str):
    thresholds = [0.25, 0.20, 0.15, 0.10]
    num_frames_to_test = 150
    lane_split_x = 640 # Assuming middle of the screen splits oncoming vs outgoing
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error opening video")
        return
        
    frames = []
    # Skip some warmup frames if necessary, maybe start at frame 50
    for _ in range(50):
        cap.read()
        
    for _ in range(num_frames_to_test):
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    print(f"Loaded {len(frames)} frames for identical comparison.")
    
    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "night_eval")
    os.makedirs(out_dir, exist_ok=True)
    
    # We will pick 3 specific frames to save across all thresholds
    save_indices = [30, 75, 120]

    results = {}

    for conf in thresholds:
        print(f"\n--- Evaluating Threshold {conf} ---")
        detector = YOLODetector(
            model_path=model_path,
            confidence_threshold=conf,
            inference_size=1280,
            device="cuda"
        )
        
        # Warmup
        _ = detector.detect(type('DummyFrame', (object,), {'data': frames[0], 'camera_id': 'test', 'timestamp': time.time(), 'frame_id': '0'})())
        
        total_dets = 0
        oncoming = 0
        outgoing = 0
        latencies = []
        conf_sum = 0.0
        
        for i, frame in enumerate(frames):
            dummy_frame = type('DummyFrame', (object,), {'data': frame, 'camera_id': 'test', 'timestamp': time.time(), 'frame_id': str(i)})()
            
            t0 = time.perf_counter()
            detections = detector.detect(dummy_frame)
            lat = time.perf_counter() - t0
            latencies.append(lat)
            
            total_dets += len(detections)
            for d in detections:
                conf_sum += d.confidence
                cx = (d.bbox_xyxy[0] + d.bbox_xyxy[2]) / 2.0
                if cx >= lane_split_x:
                    oncoming += 1
                else:
                    outgoing += 1
                    
            if i in save_indices:
                vis = frame.copy()
                for d in detections:
                    left, top, right, bottom = map(int, d.bbox_xyxy)
                    cx = (left + right) / 2
                    color = (255, 0, 0) if cx >= lane_split_x else (0, 0, 255)
                    cv2.rectangle(vis, (left, top), (right, bottom), color, 2)
                    label = f"{d.class_name} {d.confidence:.2f}"
                    cv2.putText(vis, label, (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                cv2.imwrite(os.path.join(out_dir, f"frame_{i}_conf_{conf}.jpg"), vis)
                
        avg_lat = sum(latencies) / len(latencies) if latencies else 0
        avg_conf = conf_sum / total_dets if total_dets > 0 else 0
        fps = 1.0 / avg_lat if avg_lat > 0 else 0
        
        results[conf] = {
            "total": total_dets,
            "oncoming": oncoming,
            "outgoing": outgoing,
            "avg_lat": avg_lat,
            "fps": fps,
            "avg_conf": avg_conf
        }
        
        print(f"Total Dets: {total_dets}")
        print(f"Oncoming: {oncoming}")
        print(f"Outgoing: {outgoing}")
        print(f"Avg Conf: {avg_conf:.3f}")
        print(f"Latency: {avg_lat*1000:.2f} ms")
        print(f"FPS: {fps:.1f}")

    print("\nSUMMARY:")
    for conf, stats in results.items():
        print(f"Conf {conf}: Total {stats['total']} (On: {stats['oncoming']}, Out: {stats['outgoing']}) | Avg Conf {stats['avg_conf']:.3f} | Lat {stats['avg_lat']*1000:.2f}ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--model", type=str, default="yolov8s.pt")
    args = parser.parse_args()
    
    run_threshold_eval(args.video, args.model)
