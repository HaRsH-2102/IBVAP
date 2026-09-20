import cv2
import time
import argparse
import numpy as np

from app.ingestion.opencv_stream import FileStreamManager
from app.perception.yolo_detector import YOLODetector
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline

def run_m3_audit(video_path: str, conf_thresh: float):
    print(f"Starting M3 Raw Detection Audit")
    print(f"Video: {video_path}")
    print(f"Confidence: {conf_thresh}")
    
    # Initialize M3 only
    detector = YOLODetector(
        model_path="yolov8n.pt",
        confidence_threshold=conf_thresh,
        inference_size=1280,
        device="cuda"
    )
    
    metrics = StreamMetrics()
    stream_manager = FileStreamManager("audit_cam", video_path)
    pipeline = CameraPipeline(stream_manager, metrics, playback_mode="real_time")
    
    # Check source video properties
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Source video resolution: {w}x{h}")
    cap.release()
    
    pipeline.start()
    
    window_name = f"M3 Audit - Conf: {conf_thresh}"
    # cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    frames_processed = 0
    oncoming_detected = 0
    
    try:
        while True:
            frame = pipeline.get_next_frame(timeout=1.0)
            if not frame:
                if not pipeline.is_running:
                    break
                continue
                
            vis_img = frame.data.copy()
            
            # Detect
            detections = detector.detect(frame)
            frames_processed += 1
            
            # Log raw detections count for analysis
            if frames_processed % 30 == 0:
                print(f"Frame {frames_processed}: Found {len(detections)} objects")
            
            # Draw raw detections
            # for d in detections:
            #     left, top, right, bottom = map(int, d.bbox_xyxy)
            #     color = (0, 255, 0)
            #     cv2.rectangle(vis_img, (left, top), (right, bottom), color, 2)
            #     label = f"{d.class_name} {d.confidence:.2f}"
            #     cv2.putText(vis_img, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
            # cv2.imshow(window_name, vis_img)
            
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
            
            if frames_processed > 300: # process first 300 frames to save time in background
                break
                
    finally:
        pipeline.stop()
        # cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()
    run_m3_audit(args.video, args.conf)
