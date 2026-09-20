import time
import asyncio
from app.services.validation_runner import runner

def profile_run():
    print("Starting validation runner profile...")
    video_path = r"C:\Users\Harshal\Downloads\videoplayback.mp4"
    
    runner.start_session(video_path, None)
    
    time.sleep(15) # run for 15 seconds
    import numpy as np
    stats = runner.stats
    print(f"Stats after 15 seconds: {stats}")
    print(f"Queue size: {runner.pipeline.queue_size if runner.pipeline else 0}")
    
    if runner.pipeline and runner.pipeline.metrics:
        print(f"Source FPS: {runner.pipeline.metrics.source_fps}")
        
    print("\n--- LATENCY METRICS ---")
    for k, v in runner.raw_metrics.items():
        if len(v) > 0:
            avg = np.mean(v)
            p95 = np.percentile(v, 95)
            mx = np.max(v)
            print(f"{k.upper()}: Avg={avg:.1f}ms, P95={p95:.1f}ms, Max={mx:.1f}ms")
        else:
            print(f"{k.upper()}: No data")
        
    runner.stop_session()
    print("Stopped.")

if __name__ == "__main__":
    profile_run()
