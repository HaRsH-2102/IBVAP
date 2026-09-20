"""
IBVAP — Milestone 2 Technical Validation
========================================
Runs the CameraPipeline against a local video file to validate:
- Frame decoding (OpenCV)
- Threaded decoupled capture
- Bounded buffering and frame dropping
- Real-time and max-throughput modes
- Performance metrics tracking
"""

import sys
import time
import argparse
import urllib.request
import os

# Ensure backend root is in Python path when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.config import settings

SAMPLE_VIDEO_URL = "https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4"
SAMPLE_VIDEO_PATH = "test_video.mp4"


def download_sample_video() -> None:
    """Download a sample video if it doesn't exist."""
    if not os.path.exists(SAMPLE_VIDEO_PATH):
        print(f"Downloading sample video to {SAMPLE_VIDEO_PATH}...")
        urllib.request.urlretrieve(SAMPLE_VIDEO_URL, SAMPLE_VIDEO_PATH)
        print("Download complete.")


def run_test(mode: str, processing_delay: float = 0.0, video_path: str = SAMPLE_VIDEO_PATH) -> None:
    """
    Run the pipeline validation test.
    
    Args:
        mode: 'real_time' or 'max_throughput'
        processing_delay: Artificial delay (in seconds) added to simulate slow AI processing
                          and trigger frame drops.
    """
    print(f"\n{'='*50}")
    print(f"Starting test: mode={mode}, processing_delay={processing_delay}s")
    print(f"{'='*50}")
    
    # Configure mode globally for this test run
    settings.playback_mode = mode
    
    # 1. Initialize dependencies
    metrics = StreamMetrics(window_size=30)
    stream_manager = FileStreamManager("cam_test_01", video_path)
    
    # 2. Initialize pipeline
    pipeline = CameraPipeline(stream_manager, metrics)
    
    # 3. Start pipeline
    pipeline.start()
    
    # Let it run for a bit to stabilize FPS before we start processing
    time.sleep(1.0)
    
    frames_processed = 0
    start_time = time.time()
    test_duration = float('inf')  # Run until EOF
    
    try:
        while pipeline.is_running and (time.time() - start_time) < test_duration:
            # Consumer simulation: Pull frame from pipeline
            frame = pipeline.get_next_frame(timeout=0.1)
            
            if frame:
                frames_processed += 1
                
                # Simulate AI processing time
                if processing_delay > 0:
                    time.sleep(processing_delay)
                    
            # Print metrics periodically (every ~20 frames processed)
            if frames_processed % 20 == 0 and frames_processed > 0:
                stats = metrics.get_summary()
                qsize = pipeline.queue_size
                print(f"[{mode}] "
                      f"Recv: {stats['received_fps']} FPS | "
                      f"Proc: {stats['processed_fps']} FPS | "
                      f"Drop: {stats['total_dropped']} | "
                      f"Q: {qsize}/{pipeline.buffer_capacity} | "
                      f"Lat: {stats['avg_latency_ms']} ms")
                      
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    
    # 4. Stop and Report
    pipeline.stop()
    
    print("\n--- Final Performance Report ---")
    final_stats = metrics.get_summary()
    for key, value in final_stats.items():
        print(f"{key.ljust(20)}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 2 Validation")
    parser.add_argument("--download-only", action="store_true", help="Only download sample video")
    parser.add_argument("--video", type=str, default=SAMPLE_VIDEO_PATH, help="Path to video file")
    args = parser.parse_args()

    if args.video == SAMPLE_VIDEO_PATH:
        download_sample_video()
    
    if not args.download_only:
        # Test 1: Real-time processing (simulates normal fast AI)
        run_test("real_time", processing_delay=0.0, video_path=args.video)
