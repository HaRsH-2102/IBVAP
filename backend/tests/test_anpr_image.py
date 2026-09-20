import os
import cv2
import urllib.request
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker
from app.anpr.anpr_engine import ANPREngine
from app.domain.frame import Frame
from datetime import datetime

def main():
    print("Downloading test car image...")
    # A generic car image with an Indian license plate
    url = "https://upload.wikimedia.org/wikipedia/commons/3/37/Indian_License_plate.jpg"
    img_path = "test_indian_car.jpg"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(img_path, 'wb') as out_file:
            out_file.write(response.read())
    except Exception as e:
        print(f"Failed to download image: {e}")
        return
        
    img = cv2.imread(img_path)
    if img is None:
        print("Failed to read downloaded image.")
        return
        
    print("Initializing models...")
    detector = YOLODetector(model_path="rtdetr-l.pt", confidence_threshold=0.3)
    tracker = ByteTrackTracker(camera_id="test_cam")
    anpr_engine = ANPREngine()
    
    # We simulate a few frames so the tracker can activate the track and ANPR can accumulate consensus
    for i in range(10):
        frame = Frame(
            frame_id=f"f_{i}",
            camera_id="test_cam",
            timestamp=datetime.utcnow(),
            width=img.shape[1],
            height=img.shape[0],
            data=img.copy()
        )
        
        detections = detector.detect(frame)
        
        # We need to make sure the detection is a vehicle. 
        # RT-DETR might classify this close-up as something else, or not at all if it's just a plate.
        # Wait, the wikipedia image is just a license plate, not a full vehicle! 
        # So RT-DETR-L might not detect a "car". 
        
        # Let's override the detection to force a "car" detection covering the whole image if none found
        if not any(d.class_name in ["car", "bus", "truck", "motorcycle"] for d in detections):
            from app.domain.detection import Detection
            import uuid
            d = Detection(
                detection_id=str(uuid.uuid4()),
                camera_id="test_cam",
                frame_id=f"f_{i}",
                timestamp=datetime.utcnow(),
                class_name="car",
                confidence=0.99,
                bbox_xyxy=(0.0, 0.0, float(img.shape[1]), float(img.shape[0]))
            )
            detections.append(d)
            
        tracks = tracker.update(detections, frame)
        
        anpr_events = anpr_engine.process("test_cam", frame.data, tracks, frame.timestamp)
        for evt in anpr_events:
            print(f"ANPR EVENT FIRED: {evt.plate_text} (conf: {evt.confidence:.2f})")

    print("Test complete.")

if __name__ == "__main__":
    main()
