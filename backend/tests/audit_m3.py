import os
import sys
import time
import json
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.perception.yolo_detector import YOLODetector
from app.domain.frame import Frame
from app.config import settings
from datetime import datetime, timezone

def run_m3_audit(video_path: str, output_image_path: str, conf_thresh: float):
    detector = YOLODetector(
        model_path=settings.detector_model_path,
        confidence_threshold=conf_thresh,
        inference_size=settings.detector_inference_size,
        device=settings.detector_device
    )
    
    cap = cv2.VideoCapture(video_path)
    frames_processed = 0
    total_latency = 0
    
    counts = {"person": 0, "car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    
    start_time = time.time()
    
    while cap.isOpened() and frames_processed < 50:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Wrap in Frame
        frm = Frame(
            camera_id="cam_audit",
            frame_id=f"f_{frames_processed}",
            timestamp=datetime.now(timezone.utc),
            data=frame
        )
        # Detect
        t0 = time.time()
        detections = detector.detect(frm)
        latency = time.time() - t0
        total_latency += latency
        
        # Accumulate counts
        for d in detections:
            cls = d.class_name
            if cls in counts:
                counts[cls] += 1
                
        # Save a representative frame
        if frames_processed == 25:
            vis = frame.copy()
            for d in detections:
                x1, y1, x2, y2 = map(int, d.bbox_xyxy)
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{d.class_name} {d.confidence:.2f}"
                cv2.putText(vis, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
            cv2.imwrite(output_image_path, vis)
            
        frames_processed += 1
        
    cap.release()
    
    elapsed = time.time() - start_time
    avg_fps = frames_processed / elapsed if elapsed > 0 else 0
    avg_latency = (total_latency / frames_processed * 1000) if frames_processed > 0 else 0
    
    result = {
        "video": os.path.basename(video_path),
        "avg_fps": round(avg_fps, 2),
        "avg_inference_ms": round(avg_latency, 2),
        "counts": counts
    }
    print(json.dumps(result))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--out", type=str, required=True)
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()
    
    run_m3_audit(args.video, args.out, args.conf)
