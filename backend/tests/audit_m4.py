import os
import sys
import time
import json
import cv2
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker
from app.domain.frame import Frame
from app.config import settings

def run_m4_audit(video_path: str, output_image_path: str, conf_thresh: float):
    detector = YOLODetector(
        model_path=settings.detector_model_path,
        confidence_threshold=conf_thresh,
        inference_size=settings.detector_inference_size,
        device=settings.detector_device
    )
    
    tracker = ByteTrackTracker(camera_id="cam_audit_m4", track_buffer=30)
    
    cap = cv2.VideoCapture(video_path)
    frames_processed = 0
    total_detector_latency = 0
    total_tracker_latency = 0
    max_simultaneous = 0
    
    while cap.isOpened() and frames_processed < 50:
        ret, frame = cap.read()
        if not ret:
            break
            
        frm = Frame(
            camera_id="cam_audit_m4",
            frame_id=f"f_{frames_processed}",
            timestamp=datetime.now(timezone.utc),
            data=frame
        )
        
        # Detect
        t0 = time.time()
        detections = detector.detect(frm)
        total_detector_latency += (time.time() - t0)
        
        # Track
        t1 = time.time()
        tracks = tracker.update(detections, frm)
        total_tracker_latency += (time.time() - t1)
        
        active_count = len([t for t in tracks if t.state.value == "ACTIVE"])
        if active_count > max_simultaneous:
            max_simultaneous = active_count
                
        # Save a representative frame
        if frames_processed == 25:
            vis = frame.copy()
            for t in tracks:
                if t.state.value != "ACTIVE":
                    continue
                x1, y1, x2, y2 = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 0, 0), 2)
                label = f"ID:{t.track_id.split('-')[-1]} {t.object_class.name}"
                cv2.putText(vis, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
            cv2.imwrite(output_image_path, vis)
            
        frames_processed += 1
        
    cap.release()
    
    avg_det = (total_detector_latency / frames_processed * 1000) if frames_processed > 0 else 0
    avg_trk = (total_tracker_latency / frames_processed * 1000) if frames_processed > 0 else 0
    
    result = {
        "video": os.path.basename(video_path),
        "avg_detector_ms": round(avg_det, 2),
        "avg_tracker_ms": round(avg_trk, 2),
        "total_latency_ms": round(avg_det + avg_trk, 2),
        "max_simultaneous_tracks": max_simultaneous
    }
    print(json.dumps(result))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--out", type=str, required=True)
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()
    
    run_m4_audit(args.video, args.out, args.conf)
