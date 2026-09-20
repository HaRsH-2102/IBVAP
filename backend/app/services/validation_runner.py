import os
import cv2
import json
import time
import asyncio
import threading
import queue
from datetime import datetime, timezone
import uuid
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from app.config import settings
from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker

from app.domain.zone import Zone, Point, ZoneType
from app.domain.virtual_line import VirtualLine
from app.domain.spatial import CameraSpatialConfig
from app.spatial.spatial_engine import SpatialEngine

from app.behavioral.engine import BehavioralEngine
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.loitering import LoiteringDetector

from app.domain.rule import Rule, Severity
from app.event.rule_engine import RuleEngine
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.repositories import SecurityEventRepository

from app.api.websocket import manager

class ValidationRunner:
    def __init__(self):
        self.session_id = None
        self.is_running = False
        self.pipeline = None
        self.current_frame_bytes = None
        self.lock = threading.Lock()
        self.main_loop = None
        
        self.stats = {
            "frames_processed": 0,
            "persons": 0,
            "vehicles": 0,
            "active_tracks": 0,
            "events_generated": 0,
            "event_counts": {},
            "evidence_captured": 0
        }
        self.diagnostics = {
            "video_status": "DISCONNECTED",
            "frame_decoder": "STOPPED",
            "ai_processing": "STOPPED",
            "frame_output": "STOPPED",
            "latency_ms": {}
        }
        self.session_log = []
        self.reviewer_decisions = {}
        
        self.evidence_dir = os.path.abspath(os.path.join("results", "live_validation", "evidence"))
        os.makedirs(self.evidence_dir, exist_ok=True)
        self.log_dir = os.path.abspath(os.path.join("results", "live_validation", "session_logs"))
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Async Evidence workers
        self.evidence_executor = ThreadPoolExecutor(max_workers=4)
        
        # Async DB Queue for Thread-Safety
        self.db_queue = queue.Queue()
        self.db_thread = None
        
        # Benchmarking lists
        self.raw_metrics = {
            "decode": [], "ai": [], "tracking": [], "spatial": [], "behavior": [],
            "rules": [], "annotation": [], "jpeg": [], "db": [], "evidence": [], "total": []
        }
        
    def _db_worker(self):
        # Create a thread-local database connection
        from app.domain.security import SecurityEvent, EvidencePackage
        from app.infrastructure.repositories import EvidenceRepository, SecurityEventRepository, AlertRepository
        from app.event.alert_manager import AlertManager
        from app.api.websocket import manager
        import asyncio
        
        db = SQLiteDatabase()
        repo = SecurityEventRepository(db)
        ev_repo = EvidenceRepository(db)
        alert_repo = AlertRepository(db)
        alert_manager = AlertManager(alert_repo)
        
        while self.is_running or not self.db_queue.empty():
            try:
                evt = self.db_queue.get(timeout=1.0)
                if evt is None:
                    continue
                t0 = time.perf_counter()
                if isinstance(evt, SecurityEvent):
                    repo.save(evt)
                    # Deduplicate and create alerts
                    new_alerts = alert_manager.process_events([evt])
                    # Broadcast any NEW alerts that were created
                    if self.main_loop:
                        for alert in new_alerts:
                            ws_msg = {
                                "type": "NEW_ALERT",
                                "alert": {
                                    "alert_id": alert.alert_id,
                                    "event_type": alert.event_type,
                                    "severity": alert.severity.value,
                                    "camera_id": alert.camera_id,
                                    "track_id": alert.track_id,
                                    "status": alert.status.value,
                                    "timestamp": alert.created_at.isoformat()
                                }
                            }
                            asyncio.run_coroutine_threadsafe(manager.broadcast(ws_msg), self.main_loop)
                elif isinstance(evt, EvidencePackage):
                    ev_repo.save(evt)
                self.raw_metrics["db"].append((time.perf_counter() - t0) * 1000)
                self.db_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"DB Worker Error: {e}")
                
    def start_session(self, video_id: str, loop):
        if self.is_running:
            return self.session_id
            
        self.session_id = str(uuid.uuid4())
        self.is_running = True
        self.main_loop = loop
        self.stats = {
            "frames_processed": 0, "persons": 0, "vehicles": 0,
            "active_tracks": 0, "events_generated": 0, "event_counts": {}, "evidence_captured": 0
        }
        self.diagnostics = {
            "video_status": "CONNECTED",
            "frame_decoder": "STARTING",
            "ai_processing": "STARTING",
            "frame_output": "STARTING",
            "latency_ms": {}
        }
        self.session_log = []
        self.reviewer_decisions = {}
        self.video_id = video_id
        
        # Start DB thread
        self.db_thread = threading.Thread(target=self._db_worker, daemon=True)
        self.db_thread.start()
        
        self.thread = threading.Thread(target=self._run_pipeline, args=(video_id,))
        self.thread.daemon = True
        self.thread.start()
        
        return self.session_id
        
    def stop_session(self):
        self.is_running = False
        if self.pipeline:
            self.pipeline.stop()
            
        # Ensure queue drains
        if self.db_thread:
            self.db_thread.join(timeout=3.0)

    def pause(self):
        if self.pipeline:
            self.pipeline.is_paused = True

    def resume(self):
        if self.pipeline:
            self.pipeline.is_paused = False

    def set_speed(self, speed: float):
        if self.pipeline:
            self.pipeline.playback_speed = speed

    def seek(self, timestamp_sec: float):
        if self.pipeline:
            self.pipeline.seek(timestamp_sec)
                
    def record_decision(self, event_id: str, decision: str):
        self.reviewer_decisions[event_id] = decision
        
    def _save_evidence(self, img, left, top, right, bottom, se, frame, object_class):
        t0 = time.perf_counter()
        
        event_id = se.event_id
        event_type = se.event_type
        track_id = se.track_id
        
        # SOURCE FRAME COORDINATES
        # Used for evidence generation.
        
        # Directory Structure: E:\SIH 2026\IBVAP\backend\results\evidence\{event_type}
        evidence_root = os.path.abspath(os.path.join("results", "evidence"))
        evt_dir = os.path.join(evidence_root, event_type)
        os.makedirs(evt_dir, exist_ok=True)
        
        # Crop bounds with 25% margin
        h, w = img.shape[:2]
        bw, bh = right - left, bottom - top
        mx, my = int(bw * 0.25), int(bh * 0.25)
        
        c_left = max(0, left - mx)
        c_top = max(0, top - my)
        c_right = min(w, right + mx)
        c_bottom = min(h, bottom + my)
        
        if c_right > c_left and c_bottom > c_top:
            crop_img = img[c_top:c_bottom, c_left:c_right].copy()
            
            # Red box on crop
            cv2.rectangle(crop_img, (left - c_left, top - c_top), (right - c_left, bottom - c_top), (0, 0, 255), 3)
            
            # Add black metadata panel
            panel_height = 220
            crop_h, crop_w = crop_img.shape[:2]
            
            # Ensure width is enough for text
            min_width = 600
            canvas_w = max(crop_w, min_width)
            
            canvas = np.zeros((crop_h + panel_height, canvas_w, 3), dtype=np.uint8)
            
            # Center the crop horizontally if canvas is wider
            x_offset = (canvas_w - crop_w) // 2
            canvas[:crop_h, x_offset:x_offset+crop_w] = crop_img
            
            # Draw metadata
            cv2.putText(canvas, f"EVENT: {event_type}", (20, crop_h + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(canvas, f"OBJECT: {object_class.upper()}", (20, crop_h + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(canvas, f"TRACK ID: {track_id}", (20, crop_h + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(canvas, f"CAMERA: {se.camera_id}", (300, crop_h + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(canvas, f"TIMESTAMP: {se.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", (300, crop_h + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(canvas, f"VIDEO TIME: {frame.timestamp.strftime('%H:%M:%S.%f')[:-3]}", (300, crop_h + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            desc = se.description
            # Simple text wrap for description
            cv2.putText(canvas, "WHAT HAPPENED:", (20, crop_h + 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(canvas, desc[:70], (20, crop_h + 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            if len(desc) > 70:
                cv2.putText(canvas, desc[70:140], (20, crop_h + 185), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            crop_path = os.path.join(evt_dir, f"{event_id}_crop.jpg")
            cv2.imwrite(crop_path, canvas)
        else:
            # Fallback
            crop_path = os.path.join(evt_dir, f"{event_id}_crop.jpg")
            cv2.imwrite(crop_path, img)

        # Full frame (Secondary evidence)
        full_path = os.path.join(evt_dir, f"{event_id}_full.jpg")
        # Draw red box on full frame
        cv2.rectangle(img, (left, top), (right, bottom), (0, 0, 255), 3)
        cv2.imwrite(full_path, img)
        
        # Save to DB via db_queue
        # Create EvidencePackage
        from app.domain.security import EvidencePackage
        from datetime import timedelta
        import json
        now = datetime.utcnow()
        ev_pkg = EvidencePackage(
            evidence_id=str(uuid.uuid4()),
            event_id=event_id,
            camera_id=se.camera_id,
            track_id=track_id,
            frame_id=frame.frame_id,
            timestamp=se.timestamp,
            event_type=event_type,
            object_class=object_class,
            bbox={"x1": left, "y1": top, "x2": right, "y2": bottom},
            crop_path=crop_path,
            full_frame_path=full_path,
            created_at=now,
            expires_at=now + timedelta(hours=2),
            is_saved=False,
            saved_at=None
        )
        self.db_queue.put(ev_pkg)
        
        self.raw_metrics["evidence"].append((time.perf_counter() - t0)*1000)
        
    def _run_pipeline(self, video_id: str):
        from app.infrastructure.database import SQLiteDatabase
        from app.domain.zone import ZoneType
        from app.domain.virtual_line import Direction
        import json
        
        db = SQLiteDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 1. Fetch Video Source
        cursor.execute("SELECT file_path FROM video_sources WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Video ID {video_id} not found in database")
        video_path = row["file_path"]
        self.video_path = video_path
        
        # Get video resolution
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        camera_id = video_id
        metrics = StreamMetrics(window_size=30)
        stream_manager = FileStreamManager(camera_id, video_path)
        self.pipeline = CameraPipeline(stream_manager, metrics)
        
        detector = YOLODetector(model_path="rtdetr-l.pt", confidence_threshold=0.65, device="auto")
        tracker = ByteTrackTracker(camera_id=camera_id, track_buffer=30)
        
        # 2. Load User Configured Zones
        cursor.execute("SELECT * FROM spatial_zones WHERE camera_id = ?", (camera_id,))
        zone_rows = cursor.fetchall()
        zones = []
        for z in zone_rows:
            geom_json = json.loads(z["geometry"])
            pts = [Point(x=int(p["x"] * vid_w), y=int(p["y"] * vid_h)) for p in geom_json]
            z_type = ZoneType(z["zone_type"]) if z["zone_type"] else ZoneType.RESTRICTED
            zones.append(Zone(
                zone_id=z["zone_id"], camera_id=camera_id, name=z["name"],
                zone_type=z_type, geometry=pts, active=bool(z["active"])
            ))
            
        # 3. Load User Configured Tripwires (Virtual Lines)
        cursor.execute("SELECT * FROM virtual_lines WHERE camera_id = ?", (camera_id,))
        line_rows = cursor.fetchall()
        tripwires = []
        for l in line_rows:
            pts = json.loads(l["points"])
            if len(pts) >= 2:
                start_p = Point(x=int(pts[0]["x"] * vid_w), y=int(pts[0]["y"] * vid_h))
                end_p = Point(x=int(pts[1]["x"] * vid_w), y=int(pts[1]["y"] * vid_h))
                direction = Direction(l["allowed_direction"]) if l["allowed_direction"] else Direction.BOTH
                tripwires.append(VirtualLine(
                    line_id=l["line_id"], camera_id=camera_id, name=l["name"],
                    start=start_p, end=end_p, allowed_direction=direction, active=bool(l["active"])
                ))
        
        # 4. Construct Configuration
        spatial_config = CameraSpatialConfig(camera_id=camera_id, zones=zones, tripwires=tripwires)
        spatial_engine = SpatialEngine()
        
        b_config = BehavioralConfig(loitering_duration=settings.loitering_threshold_seconds)
        behavioral_engine = BehavioralEngine(b_config, [LoiteringDetector()])
        
        rules = [
            Rule(rule_id="r1", name="Intrusion Detection", enabled=True, security_event_type="RESTRICTED_AREA_INTRUSION", severity=Severity.CRITICAL, event_type=["ZONE_ENTER"]),
            Rule(rule_id="r2", name="Loitering Detection", enabled=True, security_event_type="LOITERING", severity=Severity.HIGH, event_type=["LOITERING"]),
            Rule(rule_id="r3", name="Fence Crossing", enabled=True, security_event_type="FENCE_CROSSING", severity=Severity.HIGH, event_type=["LINE_CROSS"])
        ]
        rule_engine = RuleEngine(rules)
        
        self.pipeline.start()
        time.sleep(1.0)
        
        self.diagnostics["frame_decoder"] = "RUNNING"
        self.diagnostics["ai_processing"] = "RUNNING"
        self.diagnostics["frame_output"] = "RUNNING"
        
        last_stat_time = time.time()
        event_track_ids = set()
        
        while self.is_running and self.pipeline.is_running:
            # Latest Frame Strategy: Drain backlog queue
            frame = None
            while self.pipeline.queue_size > 0:
                frame = self.pipeline.get_next_frame(timeout=0.01)
            
            if not frame:
                frame = self.pipeline.get_next_frame(timeout=0.1)
                
            if frame:
                overall_start = time.perf_counter()
                
                # Decode Latency (not valid if frame timestamp is absolute epoch vs perf_counter)
                t_decode = time.perf_counter()
                decode_ms = 0
                
                # Use frame's video-time timestamp to ensure playback speed doesn't corrupt engine logic
                current_time = frame.timestamp
                self.stats["frames_processed"] += 1
                
                # 1. AI Inference
                t0 = time.perf_counter()
                detections = detector.detect(frame)
                ai_ms = (time.perf_counter() - t0) * 1000
                self.raw_metrics["ai"].append(ai_ms)
                
                # 2. Tracking
                t0 = time.perf_counter()
                tracks = tracker.update(detections, frame)
                trk_ms = (time.perf_counter() - t0) * 1000
                self.raw_metrics["tracking"].append(trk_ms)
                
                # 3. Spatial and Behavioral Logic
                t0 = time.perf_counter()
                spatial_events = spatial_engine.process(tracks, spatial_config)
                sp_ms = (time.perf_counter() - t0) * 1000
                
                t0 = time.perf_counter()
                behavioral_events = behavioral_engine.process(tracks, spatial_events, current_time)
                beh_ms = (time.perf_counter() - t0) * 1000
                
                self.raw_metrics["spatial"].append(sp_ms)
                self.raw_metrics["behavior"].append(beh_ms)
                
                active_tracks = [t for t in tracks if t.state.value == "ACTIVE"]
                self.stats["active_tracks"] = len(active_tracks)
                self.stats["persons"] = len([t for t in active_tracks if t.object_class == "person"])
                self.stats["vehicles"] = len([t for t in active_tracks if t.object_class in ["car", "truck", "bus", "motorcycle"]])
                
                # 4. Rules
                t_r = time.perf_counter()
                sec_events = []
                for e in spatial_events: sec_events.extend(rule_engine.evaluate(e))
                for e in behavioral_events: sec_events.extend(rule_engine.evaluate(e))
                rul_ms = (time.perf_counter() - t_r) * 1000
                self.raw_metrics["rules"].append(rul_ms)
                
                # Raw frame kept for evidence saving (unannotated baseline)
                raw_frame_copy = frame.data.copy()
                
                # 5. Annotation (Downscaled 720p to accelerate cv2 drawing)
                t0 = time.perf_counter()
                
                h_orig, w_orig = raw_frame_copy.shape[:2]
                
                # Resize first to massively speed up rectangle drawing
                vis_img_720 = cv2.resize(raw_frame_copy, (1280, 720))
                scale_x = 1280 / w_orig
                scale_y = 720 / h_orig
                
                active_track_ids = {t.track_id for t in active_tracks}
                event_track_ids = {tid for tid in event_track_ids if tid in active_track_ids} # Clean stale
                for se in sec_events:
                    if se.track_id:
                        event_track_ids.add(se.track_id)
                
                for t in active_tracks:
                    left, top, right, bottom = map(int, [t.bounding_box.left, t.bounding_box.top, t.bounding_box.right, t.bounding_box.bottom])
                    # Scale coordinates
                    s_left, s_top, s_right, s_bottom = int(left*scale_x), int(top*scale_y), int(right*scale_x), int(bottom*scale_y)
                    
                    conf = t.metadata.get('confidence', 0.0) if hasattr(t, 'metadata') and isinstance(t.metadata, dict) else 0.0
                    
                    is_event = t.track_id in event_track_ids
                    color = (0, 0, 255) if is_event else (0, 255, 0)
                    prefix = "🔴 " if is_event else ""
                    
                    # Ensure Track IDs are drawn directly beside each object
                    label = f"{prefix}{t.object_class.upper()} | ID:{t.track_id} | {conf:.2f}"
                    cv2.rectangle(vis_img_720, (s_left, s_top), (s_right, s_bottom), color, 2)
                    cv2.putText(vis_img_720, label, (s_left, s_top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                for i, se in enumerate(sec_events):
                    evt_type = se.event_type
                    track_id = se.track_id if se.track_id else "UNKNOWN"
                    evt_label = f"{evt_type} | ID: {track_id}"
                    cv2.putText(vis_img_720, evt_label, (20, 80 + (i*30)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                # 12. FRAME TIMESTAMP OVERLAY
                video_time_str = frame.timestamp.strftime('%H:%M:%S.%f')[:-3]
                sync_label1 = f"FRAME: {frame.frame_id}"
                sync_label2 = f"VIDEO TIME: {video_time_str}"
                cv2.putText(vis_img_720, sync_label1, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(vis_img_720, sync_label2, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
                ann_ms = (time.perf_counter() - t0) * 1000
                self.raw_metrics["annotation"].append(ann_ms)
                
                # Async DB and Evidence Submission
                for se in sec_events:
                    # Thread-safe DB dispatch
                    self.db_queue.put(se)
                    
                    self.stats["events_generated"] += 1
                    evt_type = se.event_type
                    self.stats["event_counts"][evt_type] = self.stats["event_counts"].get(evt_type, 0) + 1
                    
                    # Async Evidence saving (Uses Raw Frame)
                    t_match = next((tr for tr in tracks if tr.track_id == se.track_id), None)
                    obj_cls = t_match.object_class if t_match else "UNKNOWN"
                    if t_match:
                        ml, mt, mr, mb = map(int, [t_match.bounding_box.left, t_match.bounding_box.top, t_match.bounding_box.right, t_match.bounding_box.bottom])
                        self.evidence_executor.submit(self._save_evidence, raw_frame_copy.copy(), ml, mt, mr, mb, se, frame, obj_cls)
                    else:
                        self.evidence_executor.submit(self._save_evidence, raw_frame_copy.copy(), 0, 0, 0, 0, se, frame, obj_cls)
                        
                    self.stats["evidence_captured"] += 1
                    
                    evt_data = {
                        "event_id": se.event_id,
                        "type": evt_type,
                        "severity": se.severity.value,
                        "track_id": se.track_id,
                        "frame_id": frame.frame_id,
                        "timestamp": se.timestamp.isoformat(),
                        "evidence_path_full": f"/api/v1/validation/evidence/{se.event_type}/{se.event_id}_full.jpg",
                        "evidence_path_crop": f"/api/v1/validation/evidence/{se.event_type}/{se.event_id}_crop.jpg"
                    }
                    self.session_log.append(evt_data)
                    
                    if self.main_loop:
                        ws_msg = {"type": "NEW_VALIDATION_EVENT", "event": evt_data}
                        asyncio.run_coroutine_threadsafe(manager.broadcast(ws_msg), self.main_loop)
                
                # 6. JPEG Encoding (Downscaled to 75% quality)
                t0 = time.perf_counter()
                ret, buffer = cv2.imencode('.jpg', vis_img_720, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                jpg_ms = (time.perf_counter() - t0) * 1000
                self.raw_metrics["jpeg"].append(jpg_ms)
                
                tot_ms = (time.perf_counter() - overall_start) * 1000
                self.raw_metrics["total"].append(tot_ms)
                
                self.diagnostics["latency_ms"] = {
                    "decode": f"{decode_ms:.1f}",
                    "ai": f"{ai_ms:.1f}",
                    "tracking": f"{trk_ms:.1f}",
                    "spatial": f"{sp_ms:.1f}",
                    "behavior": f"{beh_ms:.1f}",
                    "rules": f"{rul_ms:.1f}",
                    "annotation": f"{ann_ms:.1f}",
                    "jpeg": f"{jpg_ms:.1f}",
                    "total": f"{tot_ms:.1f}"
                }
                
                if time.time() - last_stat_time > 1.0:
                    last_stat_time = time.time()
                    if self.main_loop:
                        asyncio.run_coroutine_threadsafe(manager.broadcast({
                            "type": "VALIDATION_STATS",
                            "stats": self.stats,
                            "diagnostics": self.diagnostics,
                            "latest_frame_id": frame.frame_id,
                            "latest_video_time": video_time_str
                        }), self.main_loop)
                
                if ret:
                    with self.lock:
                        self.current_frame_bytes = buffer.tobytes()
        
        self.diagnostics["frame_decoder"] = "STOPPED"
        self.diagnostics["ai_processing"] = "STOPPED"
        self.diagnostics["frame_output"] = "STOPPED"
        self.stop_session()

    def get_frame(self):
        with self.lock:
            return self.current_frame_bytes

runner = ValidationRunner()
