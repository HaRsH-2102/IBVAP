import os
import cv2
import csv
import json
import time
import argparse
from datetime import datetime, timezone
from collections import deque

from app.domain.video_stream import StreamState, SourceType
from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.perception.yolo_detector import YOLODetector
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

class EvidenceCollector:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.evidence_dir = os.path.join(base_dir, "evidence")
        self.modules = {
            "01_person_detection": ["detections.csv"],
            "02_person_tracking": ["tracks.csv"],
            "03_vehicle_detection": ["detections.csv"],
            "04_vehicle_tracking": ["tracks.csv"],
            "05_face_detection": ["results.csv"],
            "06_face_recognition": ["results.csv"],
            "07_anpr": ["results.csv"],
            "08_virtual_fence": ["events.json"],
            "09_suspicious_activity": ["events.json"],
            "10_night_movement": ["events.json"],
            "11_gait_recognition": ["results.csv"],
            "12_identity_fusion": ["results.json"],
            "13_alert_engine": ["alerts.json"]
        }
        
        self.module_status = {
            "01_person_detection": {"status": "FAIL", "evidence_count": 0, "notes": ""},
            "02_person_tracking": {"status": "FAIL", "evidence_count": 0, "notes": ""},
            "03_vehicle_detection": {"status": "FAIL", "evidence_count": 0, "notes": ""},
            "04_vehicle_tracking": {"status": "FAIL", "evidence_count": 0, "notes": ""},
            "05_face_detection": {"status": "NOT TESTABLE", "evidence_count": 0, "notes": "Module not integrated in current milestone"},
            "06_face_recognition": {"status": "NOT TESTABLE", "evidence_count": 0, "notes": "Module not integrated in current milestone"},
            "07_anpr": {"status": "NOT TESTABLE", "evidence_count": 0, "notes": "Module not integrated in current milestone"},
            "08_virtual_fence": {"status": "FAIL", "evidence_count": 0, "notes": ""},
            "09_suspicious_activity": {"status": "FAIL", "evidence_count": 0, "notes": ""},
            "10_night_movement": {"status": "NOT TESTABLE", "evidence_count": 0, "notes": "No night events detected"},
            "11_gait_recognition": {"status": "NOT TESTABLE", "evidence_count": 0, "notes": "Module not integrated in current milestone"},
            "12_identity_fusion": {"status": "NOT TESTABLE", "evidence_count": 0, "notes": "Module not integrated in current milestone"},
            "13_alert_engine": {"status": "FAIL", "evidence_count": 0, "notes": ""}
        }
        
        self.setup_directories()

    def setup_directories(self):
        os.makedirs(self.evidence_dir, exist_ok=True)
        for mod, files in self.modules.items():
            mod_dir = os.path.join(self.evidence_dir, mod)
            os.makedirs(mod_dir, exist_ok=True)
            for file in files:
                filepath = os.path.join(mod_dir, file)
                if file.endswith(".csv"):
                    with open(filepath, "w", newline="") as f:
                        writer = csv.writer(f)
                        if "detections" in mod:
                            writer.writerow(["frame", "timestamp", "class", "confidence", "x1", "y1", "x2", "y2"])
                        elif "tracks" in mod:
                            writer.writerow(["frame", "timestamp", "track_id", "x1", "y1", "x2", "y2"])
                elif file.endswith(".json"):
                    with open(filepath, "w") as f:
                        json.dump([], f)

    def write_csv(self, module: str, filename: str, row: list):
        with open(os.path.join(self.evidence_dir, module, filename), "a", newline="") as f:
            csv.writer(f).writerow(row)
            
    def append_json(self, module: str, filename: str, data: dict):
        filepath = os.path.join(self.evidence_dir, module, filename)
        with open(filepath, "r") as f:
            try:
                curr = json.load(f)
            except:
                curr = []
        curr.append(data)
        with open(filepath, "w") as f:
            json.dump(curr, f, indent=4)
            
    def save_image(self, module: str, filename: str, frame):
        cv2.imwrite(os.path.join(self.evidence_dir, module, filename), frame)
        self.module_status[module]["evidence_count"] += 1
        self.module_status[module]["status"] = "PASS"

    def mark_pass(self, module: str):
        self.module_status[module]["status"] = "PASS"

def run_e2e(video_path: str):
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.join("outputs", f"test_run_{timestamp_str}")
    os.makedirs(base_dir, exist_ok=True)
    
    collector = EvidenceCollector(base_dir)
    
    # Initialize components
    camera_id = "e2e_cam_1"
    stream_manager = FileStreamManager(camera_id, video_path)
    stream_manager.connect()
    fps = stream_manager.get_stream_state().fps or 30.0
    
    detector = YOLODetector(model_path="yolov8n.pt", confidence_threshold=0.25, inference_size=640, device="cuda:0")
    tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
    
    zone = Zone(
        zone_id="zone_01", camera_id=camera_id, name="Test Restriction Zone",
        zone_type=ZoneType.RESTRICTED,
        geometry=[Point(x=100, y=100), Point(x=1800, y=100), Point(x=1800, y=900), Point(x=100, y=900)]
    )
    s_config = CameraSpatialConfig(camera_id=camera_id, zones=[zone], tripwires=[])
    spatial_engine = SpatialEngine()
    
    b_config = BehavioralConfig(loitering_duration=3.0)
    behavioral_engine = BehavioralEngine(b_config, [LoiteringDetector()])
    scene_analyzer = SceneAnalyzer(NightConfig())
    
    rule_engine = RuleEngine([
        Rule(rule_id="r1", name="Zone Intrusion", enabled=True, security_event_type="ZONE_ENTRY", severity=Severity.CRITICAL, event_type=["ZONE_ENTRY"]),
        Rule(rule_id="r2", name="Loitering", enabled=True, security_event_type="LOITERING", severity=Severity.HIGH, event_type=["LOITERING"])
    ])

    
    frame_count = 0
    annotated_writer = None
    
    # Pre/Post event video rolling buffer
    frame_buffer = deque(maxlen=60) # 2 seconds
    post_event_clips = [] # list of {"module": "", "frames_left": int, "writer": VideoWriter}
    
    print(f"Starting E2E validation on {video_path}")
    
    try:
        while True:
            frame = stream_manager.read_frame()
            if frame is None:
                break
                
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Processed {frame_count} frames...")
                
            current_time = datetime.now(timezone.utc)
            frame_buffer.append(frame.data.copy())
            
            if annotated_writer is None:
                h, w = frame.data.shape[:2]
                annotated_writer = cv2.VideoWriter(
                    os.path.join(base_dir, "annotated_video.mp4"),
                    cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h)
                )

            # 1. Detection
            detections = detector.detect(frame)
            person_det_count = 0
            vehicle_det_count = 0
            for d in detections:
                if d.class_name == "person":
                    person_det_count += 1
                    collector.write_csv("01_person_detection", "detections.csv", [frame_count, current_time.isoformat(), d.class_name, d.confidence, d.bbox_xyxy[0], d.bbox_xyxy[1], d.bbox_xyxy[2], d.bbox_xyxy[3]])
                elif d.class_name in ["car", "bus", "truck", "motorcycle"]:
                    vehicle_det_count += 1
                    collector.write_csv("03_vehicle_detection", "detections.csv", [frame_count, current_time.isoformat(), d.class_name, d.confidence, d.bbox_xyxy[0], d.bbox_xyxy[1], d.bbox_xyxy[2], d.bbox_xyxy[3]])
                    
            if person_det_count > 0 and frame_count % 60 == 0:
                collector.save_image("01_person_detection", f"frame_{frame_count:06d}.jpg", frame.data)
            if vehicle_det_count > 0 and frame_count % 60 == 0:
                collector.save_image("03_vehicle_detection", f"frame_{frame_count:06d}.jpg", frame.data)

            # 2. Tracking
            tracks = tracker.update(detections, frame)
            for t in tracks:
                if t.state.value != "ACTIVE": continue
                if t.object_class.value == "person":
                    collector.write_csv("02_person_tracking", "tracks.csv", [frame_count, current_time.isoformat(), t.track_id, t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                    if frame_count % 60 == 0:
                        collector.save_image("02_person_tracking", f"tracking_frame_{frame_count:06d}.jpg", frame.data)
                elif t.object_class.value in ["car", "bus", "truck", "motorcycle"]:
                    collector.write_csv("04_vehicle_tracking", "tracks.csv", [frame_count, current_time.isoformat(), t.track_id, t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                    if frame_count % 60 == 0:
                        collector.save_image("04_vehicle_tracking", f"tracking_frame_{frame_count:06d}.jpg", frame.data)
            
            # 3. Spatial & Events
            spatial_events = spatial_engine.process(tracks, s_config)
            for ev in spatial_events:
                if ev.event_type.value == "ZONE_ENTRY":
                    ev_data = {"type": ev.event_type.value, "track_id": ev.track_id, "timestamp": current_time.isoformat(), "source": video_path, "frame": frame_count}
                    collector.append_json("08_virtual_fence", "events.json", ev_data)
                    collector.save_image("08_virtual_fence", f"intrusion_{ev.track_id}_{frame_count}.jpg", frame.data)
                    
                    # Setup clip writer
                    cw = cv2.VideoWriter(os.path.join(collector.evidence_dir, "08_virtual_fence", f"intrusion_{ev.track_id}_{frame_count}.mp4"), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                    for buf_f in frame_buffer: cw.write(buf_f)
                    post_event_clips.append({"module": "08_virtual_fence", "frames_left": int(fps*2), "writer": cw})

            behavior_events = behavioral_engine.process(tracks, spatial_events, current_time)
            for ev in behavior_events:
                if ev.behavior_type.value == "LOITERING":
                    ev_data = {"type": ev.behavior_type.value, "track_id": ev.track_id, "timestamp": current_time.isoformat(), "source": video_path, "frame": frame_count}
                    collector.append_json("09_suspicious_activity", "events.json", ev_data)
                    collector.save_image("09_suspicious_activity", f"loitering_{ev.track_id}_{frame_count}.jpg", frame.data)

            scene_state, metrics = scene_analyzer.analyze(camera_id, frame.data, current_time)
            if scene_state.name == "NIGHT":
                collector.mark_pass("10_night_movement")
                
            all_events = spatial_events + behavior_events
            alerts = []
            for ev in all_events:
                triggered = rule_engine.evaluate(ev)
                for tr in triggered:
                    alert_id = f"alert_{tr.event_id}"
                    ev_data = {"id": alert_id, "type": tr.event_type, "track_id": tr.track_id, "timestamp": current_time.isoformat(), "source": video_path, "frame": frame_count}
                    collector.append_json("13_alert_engine", "alerts.json", ev_data)
                    collector.save_image("13_alert_engine", f"alert_{alert_id}.jpg", frame.data)

            # Vis
            vis = frame.data.copy()
            for d in detections:
                left, top, right, bottom = map(int, d.bbox_xyxy)
                cv2.rectangle(vis, (left, top), (right, bottom), (255, 0, 0), 1)
            for t in tracks:
                if t.state.value != "ACTIVE": continue
                left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                cv2.rectangle(vis, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(vis, f"{t.track_id} {t.object_class.value}", (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
            
            # Post event clips logic
            active_clips = []
            for clip in post_event_clips:
                clip["writer"].write(vis)
                clip["frames_left"] -= 1
                if clip["frames_left"] > 0:
                    active_clips.append(clip)
                else:
                    clip["writer"].release()
            post_event_clips = active_clips

            annotated_writer.write(vis)
            
    finally:
        if annotated_writer: annotated_writer.release()
        for clip in post_event_clips: clip["writer"].release()
        
    generate_html_viewer(collector, base_dir)
    generate_report(collector, base_dir)
    
    print("\n" + "="*52)
    print("IBVAP E2E TEST COMPLETE")
    print("="*52)
    print(f"\nOutput:\n{base_dir}/")
    print(f"\nEvidence:\n{collector.evidence_dir}/")
    print(f"\nEvidence Viewer:\n{os.path.join(collector.evidence_dir, 'index.html')}")
    print(f"\nFinal Report:\n{os.path.join(base_dir, 'FINAL_VALIDATION_REPORT.html')}")
    print(f"\nAnnotated Video:\n{os.path.join(base_dir, 'annotated_video.mp4')}")
    print("="*52)

def generate_html_viewer(collector: EvidenceCollector, base_dir: str):
    html = ["<html><head><title>IBVAP Evidence Viewer</title><style>body{font-family:sans-serif;}</style></head><body>"]
    html.append("<h1>IBVAP E2E TEST EVIDENCE</h1>")
    
    for mod in collector.modules.keys():
        html.append(f"<h2>[{mod.replace('_', ' ').title()}]</h2>")
        mod_dir = os.path.join(collector.evidence_dir, mod)
        if not os.path.exists(mod_dir): continue
        files = os.listdir(mod_dir)
        for file in files:
            html.append(f"<p><a href='./{mod}/{file}'>{file}</a></p>")
    
    html.append("</body></html>")
    with open(os.path.join(collector.evidence_dir, "index.html"), "w") as f:
        f.write("\n".join(html))

def generate_report(collector: EvidenceCollector, base_dir: str):
    passes = sum(1 for v in collector.module_status.values() if v["status"] == "PASS")
    fails = sum(1 for v in collector.module_status.values() if v["status"] == "FAIL")
    partials = sum(1 for v in collector.module_status.values() if v["status"] == "PARTIAL")
    nt = sum(1 for v in collector.module_status.values() if v["status"] == "NOT TESTABLE")
    
    txt = [
        "IBVAP E2E VALIDATION\n",
        f"PASS: {passes}",
        f"FAIL: {fails}",
        f"NOT TESTABLE: {nt}",
        f"PARTIAL: {partials}\n",
        "| Module | Status | Evidence | Notes |",
        "|---|---|---|---|"
    ]
    for k, v in collector.module_status.items():
        txt.append(f"| {k} | {v['status']} | {v['evidence_count']} | {v['notes']} |")
        
    with open(os.path.join(base_dir, "FINAL_VALIDATION_REPORT.txt"), "w") as f:
        f.write("\n".join(txt))
        
    html = ["<html><head><title>Report</title></head><body><h1>IBVAP E2E VALIDATION</h1><pre>"]
    html.append("\n".join(txt))
    html.append("</pre></body></html>")
    with open(os.path.join(base_dir, "FINAL_VALIDATION_REPORT.html"), "w") as f:
        f.write("\n".join(html))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    args = parser.parse_args()
    run_e2e(args.video)
