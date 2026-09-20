import sys
import time
import os
import argparse
import cv2

# Ensure backend root is in Python path when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.config import settings

def run_m2_audit(video_path: str, out_img: str):
    settings.playback_mode = "real_time"
    metrics = StreamMetrics(window_size=30)
    stream_manager = FileStreamManager("cam_test_01", video_path)
    pipeline = CameraPipeline(stream_manager, metrics)
    pipeline.start()
    
    time.sleep(1.0)
    start_time = time.time()
    frames_processed = 0
    saved = False
    
    print("Running M2 Camera Pipeline...")
    while pipeline.is_running and (time.time() - start_time) < 5.0:
        frame = pipeline.get_next_frame(timeout=0.1)
        if frame:
            if not saved and frame.data is not None:
                cv2.imwrite(out_img, frame.data)
                print(f"Saved visual evidence to {out_img}")
                saved = True
            frames_processed += 1
            
    pipeline.stop()
    
    print("\n--- M2 Final Performance Report ---")
    final_stats = metrics.get_summary()
    for key, value in final_stats.items():
        print(f"{key.ljust(20)}: {value}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, default=r"C:\Users\Harshal\Downloads\videoplayback.mp4")
    parser.add_argument("--out", type=str, default=r"E:\SIH 2026\IBVAP\artifacts\full_system_audit\m2\m2_frame.jpg")
    args = parser.parse_args()
    run_m2_audit(args.video, args.out)
