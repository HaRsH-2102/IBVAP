import time
import sys
import os
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.behavioral.config import BehavioralConfig
from app.behavioral.engine import BehavioralEngine
from app.behavioral.detectors import (
    LoiteringDetector, StationaryDetector, RestrictedZoneDwellDetector,
    RepeatedZoneEntryDetector, BoundaryApproachDetector, DirectionDetector
)
from app.domain.zone import Point
from collections import namedtuple

# Mocks
Track = namedtuple('Track', ['camera_id', 'track_id', 'state', 'bounding_box'])
State = namedtuple('State', ['value'])
Box = namedtuple('Box', ['left', 'top', 'right', 'bottom'])

def run_benchmark():
    config = BehavioralConfig()
    engine = BehavioralEngine(
        config=config,
        detectors=[
            LoiteringDetector(),
            StationaryDetector(),
            RestrictedZoneDwellDetector(),
            RepeatedZoneEntryDetector(),
            BoundaryApproachDetector(),
            DirectionDetector()
        ]
    )
    
    track_counts = [1, 5, 10, 20, 50, 100]
    frames_to_run = 100
    
    print("=== M7 Latency Benchmark ===")
    
    for count in track_counts:
        # Reset engine
        engine.track_states.clear()
        
        tracks = []
        for i in range(count):
            tracks.append(Track("cam1", f"trk_{i}", State("ACTIVE"), Box(0, 0, 10, 10)))
            
        t0 = datetime.now()
        
        # Warmup
        for f in range(10):
            engine.process(tracks, [], t0 + timedelta(seconds=f*0.1))
            
        # Benchmark
        start_time = time.perf_counter()
        for f in range(frames_to_run):
            engine.process(tracks, [], t0 + timedelta(seconds=(f+10)*0.1))
        end_time = time.perf_counter()
        
        total_time_ms = (end_time - start_time) * 1000
        avg_per_frame_ms = total_time_ms / frames_to_run
        avg_per_track_per_frame_ms = avg_per_frame_ms / count
        
        print(f"Tracks: {count:3} | Total Latency for {frames_to_run} frames: {total_time_ms:.2f}ms | Avg per frame: {avg_per_frame_ms:.3f}ms | Avg per track/frame: {avg_per_track_per_frame_ms:.4f}ms")

if __name__ == "__main__":
    run_benchmark()
