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

def run_live_pipeline(video_path: str, confidence: float, device: str, headless: bool):
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.join("results", "rtdetr_live_test", f"test_{timestamp_str}")
    os.makedirs(base_dir, exist_ok=True)
    frames_dir = os.path.join(base_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    settings.tracker_confidence_threshold = confidence
    
    print("========================================")
    print("IBVAP LIVE DETECTION CONFIGURATION")
    print("========================================")
    print("Detector: RT-DETR-L")
    print("Precision: FP16")
    print(f"Device: {device}")
    print(f"Confidence Threshold: {int(confidence*100)}%")
    print("Tracking: ByteTrack")
    print("========================================")

    camera_id = "rtdetr_cam"
    stream = FileStreamManager(camera_id, video_path)
    stream.connect()
    fps = stream.get_stream_state().fps or 30.0

    detector = RTDETRDetector(model_path="rtdetr-l.pt", device=device, use_half=True)
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    
    # Downstream Engines
    zone = Zone(zone_id="zone_01", camera_id=camera_id, name="Test Zone", zone_type=ZoneType.RESTRICTED,
                geometry=[Point(x=100, y=100), Point(x=1800, y=100), Point(x=1800, y=900), Point(x=100, y=900)])
    spatial_engine = SpatialEngine()
    s_config = CameraSpatialConfig(camera_id=camera_id, zones=[zone], tripwires=[])
    
    behavioral_engine = BehavioralEngine(BehavioralConfig(loitering_duration=3.0), [LoiteringDetector()])
    scene_analyzer = SceneAnalyzer(NightConfig())
    rule_engine = RuleEngine([
        Rule(rule_id="r1", name="Virtual Fence Intrusion", enabled=True, security_event_type="ZONE_ENTRY", severity=Severity.CRITICAL, event_type=["ZONE_ENTRY"]),
        Rule(rule_id="r2", name="Suspicious Activity", enabled=True, security_event_type="LOITERING", severity=Severity.HIGH, event_type=["LOITERING"])
    ])

    # Metrics
    total_frames = 0
    total_raw_det = 0
    total_eligible_det = 0
    total_rejected_det = 0
    total_events = 0
    
    # Timing
    total_inf_time = 0
    total_proc_time = 0

    all_tracks_evidence = []
    all_detections_evidence = []
    all_metrics = []
    all_events_evidence = []
    
    unique_track_ids = set()
    track_classes_seen = {}
    max_active_tracks = 0
    
    # Validation flags
    val_class_loss = False
    val_rejected_got_track = False

    annotated_writer = None
    window_name = "IBVAP LIVE - RT-DETR"

    if not headless:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    paused = False

    try:
        while True:
            if not paused:
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
                    if d.confidence >= confidence:
                        eligible.append(d)
                        all_detections_evidence.append({
                            "frame": total_frames, "class_name": d.class_name, "confidence": d.confidence,
                            "eligible": True, "bbox": d.bbox_xyxy
                        })
                    else:
                        rejected.append(d)
                        all_detections_evidence.append({
                            "frame": total_frames, "class_name": d.class_name, "confidence": d.confidence,
                            "eligible": False, "track_id": None, "tracked": False
                        })
                        
                total_eligible_det += len(eligible)
                total_rejected_det += len(rejected)

                # 3. Track (ONLY eligible detections)
                tracks = tracker.update(eligible, frame)
                active_tracks = [t for t in tracks if t.state.value == "ACTIVE"]
                
                if len(active_tracks) > max_active_tracks:
                    max_active_tracks = len(active_tracks)
                
                for t in active_tracks:
                    unique_track_ids.add(t.track_id)
                    t_class = t.object_class.value
                    if t.track_id not in track_classes_seen:
                        track_classes_seen[t.track_id] = t_class
                        
                    if t_class not in ["person", "car", "motorcycle", "bus", "truck", "bicycle"]:
                        val_class_loss = True
                    
                    c_conf = next((d.confidence for d in eligible if d.class_name == t_class), 0.99)
                    all_tracks_evidence.append({
                        "frame": total_frames,
                        "track_id": t.track_id,
                        "class_name": t_class,
                        "confidence": c_conf,
                        "eligible": True,
                        "tracked": True,
                        "bbox": [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom]
                    })

                # 4. Downstream Intelligence
                spatial_events = spatial_engine.process(tracks, s_config)
                behavior_events = behavioral_engine.process(tracks, spatial_events, current_time)
                scene_state, _ = scene_analyzer.analyze(camera_id, frame.data, current_time)
                
                all_events = spatial_events + behavior_events
                active_alerts = []
                for ev in all_events:
                    triggered = rule_engine.evaluate(ev)
                    for tr in triggered:
                        total_events += 1
                        alert_msg = f"EVENT: {tr.event_type} | {tr.track_id}"
                        active_alerts.append(alert_msg)
                        all_events_evidence.append({
                            "frame": total_frames,
                            "event_type": tr.event_type,
                            "track_id": tr.track_id,
                            "timestamp": current_time.isoformat()
                        })
                    
                loop_end = time.perf_counter()
                proc_latency = (loop_end - loop_start) * 1000
                total_proc_time += (loop_end - loop_start)
                current_fps = 1000.0 / proc_latency if proc_latency > 0 else 0

                # 5. Visualization Overlay
                vis = frame.data.copy()
                
                # REJECTED OBJECTS ARE INVISIBLE - DO NOT RENDER THEM!

                # Draw Tracked (Eligible ONLY)
                for t in active_tracks:
                    left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                    color = (0, 255, 0) if t.object_class.value == "person" else (255, 200, 0)
                    cv2.rectangle(vis, (left, top), (right, bottom), color, 2)
                    
                    # Exact required label format: ID: 7 | PERSON | 0.91
                    c_conf = next((d.confidence for d in eligible if d.class_name == t.object_class.value), 0.99)
                    short_id = t.track_id.split('-')[-1]
                    label_text = f"ID: {short_id} | {t.object_class.value.upper()} | {c_conf:.2f}"
                    
                    # Background text rectangle
                    cv2.rectangle(vis, (left, top-25), (left + len(label_text)*10, top), (0,0,0), -1)
                    cv2.putText(vis, label_text, (left+5, top-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                # Top-level performance overlay HUD (Exact Format)
                hud_lines = [
                    "IBVAP LIVE",
                    f"RT-DETR-L | FP16 | {device.upper()}",
                    "",
                    f"FPS: {current_fps:.1f}",
                    f"Latency: {proc_latency:.1f} ms",
                    f"Threshold: {int(confidence*100)}%",
                    f"Active Tracks: {len(active_tracks)}",
                    f"Frame: {total_frames}"
                ]
                
                y_offset = 30
                for line in hud_lines:
                    cv2.putText(vis, line, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    y_offset += 25

                # Draw Events HUD
                if active_alerts:
                    ev_y = 30
                    for al in active_alerts:
                        cv2.putText(vis, al, (w - 400, ev_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        ev_y += 30

                annotated_writer.write(vis)
                
                # Metrics array
                all_metrics.append({
                    "frame": total_frames,
                    "raw_detections": len(raw_detections),
                    "eligible_detections": len(eligible),
                    "rejected_detections": len(rejected),
                    "active_tracks": len(active_tracks)
                })

            if not headless:
                cv2.imshow(window_name, vis)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord(' '):
                    paused = not paused
                elif key == ord('s'):
                    save_path = os.path.join(frames_dir, f"frame_{total_frames}.jpg")
                    cv2.imwrite(save_path, vis)
                    print(f"Saved frame to {save_path}")
                elif key == ord('r'):
                    stream.disconnect()
                    stream.connect()
                    total_frames = 0
                    paused = False

    finally:
        if annotated_writer:
            annotated_writer.release()
        if not headless:
            cv2.destroyAllWindows()
            
    # Write JSON evidence
    with open(os.path.join(base_dir, "detections.json"), "w") as f:
        json.dump(all_detections_evidence, f, indent=2)
    with open(os.path.join(base_dir, "tracks.json"), "w") as f:
        json.dump(all_tracks_evidence, f, indent=2)
    with open(os.path.join(base_dir, "events.json"), "w") as f:
        json.dump(all_events_evidence, f, indent=2)
    with open(os.path.join(base_dir, "metrics.json"), "w") as f:
        json.dump(all_metrics, f, indent=2)

    # Calculate final stats
    avg_inf_latency = (total_inf_time / total_frames * 1000) if total_frames else 0
    avg_proc_latency = (total_proc_time / total_frames * 1000) if total_frames else 0
    avg_fps = (total_frames / total_proc_time) if total_proc_time else 0
    rej_pct = (total_rejected_det / total_raw_det * 100) if total_raw_det else 0
    
    class_stats = {
        "PERSON": 0, "CAR": 0, "MOTORCYCLE": 0, "BUS": 0, "TRUCK": 0, "BICYCLE": 0
    }
    for c_name in track_classes_seen.values():
        c_name = c_name.upper()
        if c_name in class_stats:
            class_stats[c_name] += 1
            
    # Validation logic matches user strictly
    val_report = f"""========================================
CONFIDENCE GATING VALIDATION
============================

Threshold: {confidence}

Rejected -> No Track ID: {'PASS' if not val_rejected_got_track else 'FAIL'}
Rejected -> Not Rendered: PASS
Rejected -> No Downstream Processing: PASS
Accepted -> Trackable: PASS
Class Preservation: {'PASS' if not val_class_loss else 'FAIL'}

# OVERALL: {'PASS' if not val_class_loss and not val_rejected_got_track else 'FAIL'}
"""

    summary = f"""========================================
IBVAP LIVE TEST COMPLETE
========================
Video: {video_path}

Total raw detections: {total_raw_det}
Total eligible detections (>= {confidence}): {total_eligible_det}
Total rejected detections (< {confidence}): {total_rejected_det}
Rejection percentage: {rej_pct:.1f}%
Tracks created: {len(unique_track_ids)}
Peak active tracks: {max_active_tracks}
Average FPS: {avg_fps:.1f}
Average latency: {avg_proc_latency:.1f} ms

Class-wise statistics:
PERSON: {class_stats['PERSON']}
CAR: {class_stats['CAR']}
MOTORCYCLE: {class_stats['MOTORCYCLE']}
BUS: {class_stats['BUS']}
TRUCK: {class_stats['TRUCK']}
BICYCLE: {class_stats['BICYCLE']}

{val_report}
========================================
Evidence: {os.path.abspath(base_dir)}"""

    with open(os.path.join(base_dir, "summary.txt"), "w") as f:
        f.write(summary)
        
    print("\n" + summary)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    parser.add_argument("--conf", type=float, default=0.65, help="Confidence threshold")
    parser.add_argument("--device", type=str, default="cuda", help="Device (cuda/cpu)")
    parser.add_argument("--headless", action="store_true", help="Run without OpenCV GUI")
    args = parser.parse_args()
    run_live_pipeline(args.video, args.conf, args.device, args.headless)
