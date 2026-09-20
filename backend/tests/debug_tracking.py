import sys
import os
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker

def debug_first_frame():
    video_path = r"C:\Users\Harshal\Downloads\videoplayback.mp4"
    
    stream_manager = FileStreamManager("cam_debug", video_path)
    metrics = StreamMetrics(window_size=30)
    pipeline = CameraPipeline(stream_manager, metrics)
    pipeline.start()
    
    detector = YOLODetector(
        model_path="yolov8n.pt",
        confidence_threshold=0.25,
        inference_size=1280,
        device="auto"
    )
    
    tracker = ByteTrackTracker(camera_id="cam_debug", track_buffer=30)
    
    import time
    time.sleep(1.0)
    
    # Drain
    while True:
        f = pipeline.get_next_frame(timeout=0.0)
        if f is None:
            break

    print("\n--- 10 Frame Sequence Test ---")
    for frame_idx in range(10):
        frame = None
        while not frame:
            frame = pipeline.get_next_frame(timeout=0.1)
            
        detections = detector.detect(frame)
        tracks = tracker.update(detections, frame)
        
        # Find Track 1
        track1 = next((t for t in tracks if t.track_id.endswith("-1")), None)
        if track1:
            left = int(track1.bounding_box.left)
            top = int(track1.bounding_box.top)
            right = int(track1.bounding_box.right)
            bottom = int(track1.bounding_box.bottom)
            print(f"Frame {frame_idx}: Track 1 at [L:{left}, T:{top}, R:{right}, B:{bottom}], State={track1.state.name}")
        else:
            print(f"Frame {frame_idx}: Track 1 missing")
            
    pipeline.stop()

if __name__ == "__main__":
    debug_first_frame()
