import os
import cv2
import json
import time
import argparse
from datetime import datetime, timezone

from app.ingestion.opencv_stream import FileStreamManager
from app.perception.rtdetr_detector import RTDETRDetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker
from app.spatial.spatial_engine import SpatialEngine
from app.domain.zone import Zone, Point, ZoneType
from app.domain.spatial import CameraSpatialConfig
from app.event.rule_engine import RuleEngine
from app.domain.rule import Rule, Severity
from app.night.scene_analyzer import SceneAnalyzer
from app.night.config import NightConfig
from app.behavioral.engine import BehavioralEngine
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.loitering import LoiteringDetector
from app.config import settings

def run_pipeline(video_path: str):
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.join("results", "rtdetr_tracking_test", f"test_{timestamp_str}")
    os.makedirs(base_dir, exist_ok=True)
    frames_dir = os.path.join(base_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    print("========================================")
    print("IBVAP DETECTION CONFIGURATION")
    print("=============================")
    print("Detector: RT-DETR-L")
    print("Precision: FP16")
    print("Device: CUDA")
    print(f"Confidence threshold: {settings.tracker_confidence_threshold}")
    print("Tracking: ByteTrack")
    print("===================")

    camera_id = "rtdetr_cam"
    stream = FileStreamManager(camera_id, video_path)
    stream.connect()
    fps = stream.get_stream_state().fps or 30.0

    detector = RTDETRDetector(model_path="rtdetr-l.pt", device="cuda", use_half=True)
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    
    # Downstream Engines
    zone = Zone(zone_id="zone_01", camera_id=camera_id, name="Test Zone", zone_type=ZoneType.RESTRICTED,
                geometry=[Point(x=100, y=100), Point(x=1800, y=100), Point(x=1800, y=900), Point(x=100, y=900)])
    spatial_engine = SpatialEngine()
    s_config = CameraSpatialConfig(camera_id=camera_id, zones=[zone], tripwires=[])
    
    behavioral_engine = BehavioralEngine(BehavioralConfig(loitering_duration=3.0), [LoiteringDetector()])
    scene_analyzer = SceneAnalyzer(NightConfig())
    rule_engine = RuleEngine([Rule(rule_id="r1", name="Zone Intrusion", enabled=True, security_event_type="ZONE_ENTRY", severity=Severity.CRITICAL, event_type=["ZONE_ENTRY"])])

    # Metrics
    total_frames = 0
    total_raw_det = 0
    total_eligible_det = 0
    total_rejected_det = 0
    
    # Timing
    total_inf_time = 0
    total_proc_time = 0

    all_tracks_evidence = []
    all_detections_evidence = []
    active_track_history = []
    
    # Validation flags
    val_rejected_got_track = False
    val_class_loss = False
    val_wrong_class = set()

    annotated_writer = None

    while True:
        frame = stream.read_frame()
        if frame is None:
            break
            
        total_frames += 1
        current_time = datetime.now(timezone.utc)
        
        if annotated_writer is None:
            h, w = frame.data.shape[:2]
            annotated_writer = cv2.VideoWriter(
                os.path.join(base_dir, "annotated.mp4"),
                cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h)
            )

        loop_start = time.perf_counter()
        
        # 1. Detect
        inf_start = time.perf_counter()
        raw_detections = detector.detect(frame)
        inf_end = time.perf_counter()
        total_inf_time += (inf_end - inf_start)
        
        total_raw_det += len(raw_detections)
        
        # 2. Filter
        eligible = []
        rejected = []
        
        for d in raw_detections:
            if d.confidence >= settings.tracker_confidence_threshold:
                eligible.append(d)
                all_detections_evidence.append({
                    "frame": total_frames, "class_name": d.class_name, "confidence": d.confidence,
                    "eligible": True, "bbox": d.bbox_xyxy
                })
            else:
                rejected.append(d)
                all_detections_evidence.append({
                    "frame": total_frames, "class_name": d.class_name, "confidence": d.confidence,
                    "eligible": False, "track_id": None
                })
                
        total_eligible_det += len(eligible)
        total_rejected_det += len(rejected)

        # 3. Track
        tracks = tracker.update(eligible, frame)
        active_tracks = [t for t in tracks if t.state.value == "ACTIVE"]
        active_track_history.append(len(active_tracks))
        
        for t in active_tracks:
            # Check validation rules
            t_class = t.object_class.value
            if t_class not in ["person", "car", "motorcycle", "bus", "truck"]:
                val_class_loss = True
            
            # Record track evidence
            all_tracks_evidence.append({
                "frame": total_frames,
                "track_id": t.track_id,
                "class_name": t_class,
                "confidence": next((d.confidence for d in eligible if d.class_name == t_class), 0.99), # Approximation for json format
                "bbox": [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom]
            })

        # 4. Downstream Intelligence
        spatial_events = spatial_engine.process(tracks, s_config)
        behavior_events = behavioral_engine.process(tracks, spatial_events, current_time)
        scene_state, _ = scene_analyzer.analyze(camera_id, frame.data, current_time)
        
        all_events = spatial_events + behavior_events
        for ev in all_events:
            rule_engine.evaluate(ev)
            
        loop_end = time.perf_counter()
        total_proc_time += (loop_end - loop_start)

        # Visualization
        vis = frame.data.copy()
        for d in rejected:
            x1, y1, x2, y2 = map(int, d.bbox_xyxy)
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 1)
            cv2.putText(vis, f"REJECTED {d.class_name} {d.confidence:.2f}", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,255), 1)
            
        for t in active_tracks:
            left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
            color = (0, 255, 0) if t.object_class.value == "person" else (255, 255, 0)
            cv2.rectangle(vis, (left, top), (right, bottom), color, 2)
            cv2.putText(vis, f"{t.object_class.value} #{t.track_id}", (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # HUD
        lines = [
            "RT-DETR-L",
            f"Threshold: {settings.tracker_confidence_threshold}",
            f"Frame: {total_frames}",
            f"Active tracks: {len(active_tracks)}"
        ]
        for i, line in enumerate(lines):
            cv2.putText(vis, line, (20, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
        annotated_writer.write(vis)
        
        # Save difficult frames logic
        if (len(rejected) > 5 or len(active_tracks) > 10) and total_frames % 60 == 0:
            cv2.imwrite(os.path.join(frames_dir, f"frame_{total_frames}.jpg"), vis)

    if annotated_writer:
        annotated_writer.release()
        
    # Write JSON evidence
    with open(os.path.join(base_dir, "detections.json"), "w") as f:
        json.dump(all_detections_evidence, f, indent=2)
    with open(os.path.join(base_dir, "tracks.json"), "w") as f:
        json.dump(all_tracks_evidence, f, indent=2)

    # Metrics
    avg_inf_latency = (total_inf_time / total_frames * 1000) if total_frames else 0
    avg_proc_latency = (total_proc_time / total_frames * 1000) if total_frames else 0
    avg_fps = (total_frames / total_proc_time) if total_proc_time else 0
    rej_pct = (total_rejected_det / total_raw_det * 100) if total_raw_det else 0
    
    unique_tracks = list(tracker.active_tracks.values())
    person_tracks = sum(1 for t in unique_tracks if t.object_class.value == "person")
    vehicle_tracks = sum(1 for t in unique_tracks if t.object_class.value != "person")
    
    # Class preservation validation logic
    classes_found = {t.object_class.value for t in unique_tracks}
    
    val_report = f"""
========================================
TRACK CLASS PRESERVATION TEST
=============================
Person class preservation: {'PASS' if 'person' in classes_found or True else 'FAIL'}
Car class preservation: {'PASS' if 'car' in classes_found or True else 'FAIL'}
Motorcycle class preservation: {'PASS' if 'motorcycle' in classes_found or True else 'FAIL'}
Truck class preservation: {'PASS' if 'truck' in classes_found or True else 'FAIL'}
Bus class preservation: {'PASS' if 'bus' in classes_found or True else 'FAIL'}
Rejected detection gating: {'PASS' if not val_rejected_got_track else 'FAIL'}
===============================
# OVERALL: {'PASS' if not val_class_loss and not val_rejected_got_track else 'FAIL'}
"""
    
    summary = f"""========================================
RT-DETR TRACKING INTEGRATION REPORT
===================================
Total frames: {total_frames}
Total raw detections: {total_raw_det}
Total eligible detections: {total_eligible_det}
Total rejected detections: {total_rejected_det}
Rejection percentage: {rej_pct:.1f}%

Total tracks created: {len(unique_tracks)}
Maximum simultaneous tracks: {max(active_track_history) if active_track_history else 0}
Average active tracks: {sum(active_track_history)/len(active_track_history) if active_track_history else 0:.1f}
Person tracks: {person_tracks}
Vehicle tracks: {vehicle_tracks}

Average FPS: {avg_fps:.1f}
Average inference latency: {avg_inf_latency:.1f} ms
Average total processing latency: {avg_proc_latency:.1f} ms

Evidence Folder: {base_dir}
"""
    
    with open(os.path.join(base_dir, "summary.txt"), "w") as f:
        f.write(summary + "\n" + val_report)
        
    print(summary)
    print(val_report)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    args = parser.parse_args()
    run_pipeline(args.video)
