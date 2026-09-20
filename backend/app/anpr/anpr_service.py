import threading
import queue
import time
import logging
import re
from typing import Optional, Dict, Any, List
import numpy as np

from app.domain.security import SecurityEvent
from app.infrastructure.database import SQLiteDatabase
from app.domain.system_config import SystemConfiguration
from app.perception.plate_detector import PlateDetector
from app.anpr.engines.adapters import PaddleOCRAdapter

logger = logging.getLogger("IBVAP.ANPRService")

class ANPRRequest:
    def __init__(self, security_event: SecurityEvent, frame: Optional[np.ndarray]):
        self.security_event = self._copy_event(security_event)
        # Deep copy the frame so the main pipeline can reuse its buffers safely
        self.frame = np.copy(frame) if frame is not None else None
        self.enqueue_time = time.perf_counter()
        
    def _copy_event(self, event: SecurityEvent) -> SecurityEvent:
        return SecurityEvent(
            event_id=event.event_id,
            source_spatial_event_id=event.source_spatial_event_id,
            rule_id=event.rule_id,
            event_type=event.event_type,
            severity=event.severity,
            camera_id=event.camera_id,
            track_id=event.track_id,
            timestamp=event.timestamp,
            correlation_id=event.correlation_id,
            metadata=dict(event.metadata) if event.metadata else {},
            status=event.status
        )

class ANPRWorker(threading.Thread):
    def __init__(self, config: SystemConfiguration, db: SQLiteDatabase):
        super().__init__(name="ANPRWorkerThread")
        self.config = config
        self.db = db
        queue_size = getattr(config, "anpr_queue_size", 50)
        self.queue = queue.Queue(maxsize=queue_size)
        self.running = False
        
        self.plate_detector = PlateDetector(
            confidence_threshold=getattr(config, "anpr_detector_confidence", 0.50),
            device=getattr(config, "detector_device", "auto")
        )
        self.ocr_engine = PaddleOCRAdapter()
        
        self.metrics = {
            "jobs_processed": 0,
            "jobs_dropped": 0,
            "plates_detected": 0,
            "ocr_success": 0,
            "errors": 0,
            "total_latency_ms": 0.0
        }
        
        self.consensus_memory: Dict[str, List[str]] = {}

    def enqueue(self, req: ANPRRequest) -> bool:
        try:
            self.queue.put_nowait(req)
            return True
        except queue.Full:
            self.metrics["jobs_dropped"] += 1
            logger.warning(f"ANPR_QUEUE_FULL: Dropping ANPR job for event {req.security_event.event_id}")
            return False

    def run(self):
        self.running = True
        logger.info("ANPR Worker thread started.")
        while self.running:
            try:
                req = self.queue.get(timeout=1.0)
                if req is None:
                    continue
            except queue.Empty:
                continue

            try:
                self._process_job(req)
            except Exception as e:
                self.metrics["errors"] += 1
                logger.error(f"ANPR_FAILED for event {req.security_event.event_id}: {e}")
                self._save_result(req.security_event, status="ERROR", latency_ms=0)
            finally:
                self.queue.task_done()
                self.metrics["jobs_processed"] += 1

    def _normalize_indian_plate(self, text: str) -> str:
        if not text:
            return ""
        t = text.upper()
        t = re.sub(r'[\s\.\-\,]+', '', t)
        return t

    def _process_job(self, req: ANPRRequest):
        t0 = time.perf_counter()
        ev = req.security_event
        
        if req.frame is None:
            logger.debug(f"Event {ev.event_id} has no frame. Skipping ANPR.")
            self._save_result(ev, status="NO_FRAME", latency_ms=(time.perf_counter()-t0)*1000)
            return

        evidence_meta = ev.metadata.get("evidence", {})
        bbox = evidence_meta.get("bounding_box")
        if not bbox:
            logger.debug(f"Event {ev.event_id} missing bounding box. Skipping ANPR.")
            self._save_result(ev, status="NO_BBOX", latency_ms=(time.perf_counter()-t0)*1000)
            return

        x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
        H, W, _ = req.frame.shape
        
        pad = 20
        c_left = max(0, x1 - pad)
        c_top = max(0, y1 - pad)
        c_right = min(W, x2 + pad)
        c_bottom = min(H, y2 + pad)
        
        vehicle_crop = req.frame[c_top:c_bottom, c_left:c_right]
        if vehicle_crop.size == 0:
            self._save_result(ev, status="INVALID_CROP", latency_ms=(time.perf_counter()-t0)*1000)
            return

        logger.info(f"ANPR_DETECTION_STARTED for {ev.event_id}")
        t_det_start = time.perf_counter()
        plate_results = self.plate_detector.detect_in_crop(vehicle_crop)
        t_det_end = time.perf_counter()
        
        if not plate_results:
            logger.info(f"ANPR_UNREADABLE (No Plate) for {ev.event_id}")
            self._save_result(ev, status="NO_PLATE", latency_ms=(time.perf_counter()-t0)*1000)
            return
            
        self.metrics["plates_detected"] += 1
        logger.info(f"ANPR_DETECTION_COMPLETE for {ev.event_id} in {(t_det_end-t_det_start)*1000:.1f}ms")
        
        best_plate = max(plate_results, key=lambda p: p[4])
        px1, py1, px2, py2, p_conf = best_plate
        
        # Calculate padding (15% of width and height)
        pw = px2 - px1
        ph = py2 - py1
        pad_x = pw * 0.15
        pad_y = ph * 0.15
        
        # Crop from the vehicle crop with padding
        c_px1 = max(0, int(px1 - pad_x))
        c_py1 = max(0, int(py1 - pad_y))
        c_px2 = min(vehicle_crop.shape[1], int(px2 + pad_x))
        c_py2 = min(vehicle_crop.shape[0], int(py2 + pad_y))
        
        plate_crop = vehicle_crop[c_py1:c_py2, c_px1:c_px2]
        
        abs_px1 = c_left + int(px1)
        abs_py1 = c_top + int(py1)
        abs_px2 = c_left + int(px2)
        abs_py2 = c_top + int(py2)
        
        # Save plate crop to disk
        from datetime import datetime
        import os
        import cv2
        date_str = datetime.fromisoformat(ev.timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        evidence_dir = os.path.join(self.config.storage_base_path, "evidence", ev.camera_id, date_str, ev.event_id)
        os.makedirs(evidence_dir, exist_ok=True)
        
        plate_crop_path = os.path.join(evidence_dir, f"{ev.event_id}_plate.jpg")
        cv2.imwrite(plate_crop_path, plate_crop)
        
        logger.info(f"ANPR_OCR_STARTED for {ev.event_id}")
        t_ocr_start = time.perf_counter()
        
        if not self.ocr_engine.is_available:
            self._save_result(ev, status="OCR_ENGINE_UNAVAILABLE", plate_conf=p_conf, 
                              plate_bbox=[abs_px1, abs_py1, abs_px2, abs_py2], 
                              plate_crop_path=plate_crop_path,
                              latency_ms=(time.perf_counter()-t0)*1000)
            return
            
        ocr_result_dict = self.ocr_engine.process_crop(plate_crop, ev.event_id, ev.camera_id, ev.track_id)
        t_ocr_end = time.perf_counter()
        
        if ocr_result_dict.get("status") != "SUCCESS" or not ocr_result_dict.get("raw_text"):
            logger.info(f"ANPR_OCR_FAILED for {ev.event_id}")
            self._save_result(ev, status="OCR_FAILED", plate_conf=p_conf, 
                              plate_bbox=[abs_px1, abs_py1, abs_px2, abs_py2], 
                              plate_crop_path=plate_crop_path,
                              latency_ms=(time.perf_counter()-t0)*1000)
            return
            
        raw_text = ocr_result_dict["raw_text"]
        ocr_conf = ocr_result_dict.get("ocr_confidence", 0.0)
        
        logger.info(f"ANPR_OCR_COMPLETE for {ev.event_id} in {(t_ocr_end-t_ocr_start)*1000:.1f}ms")
        
        norm_text = self._normalize_indian_plate(raw_text)
        if not norm_text:
            self._save_result(ev, status="UNREADABLE", plate_conf=p_conf, 
                              plate_bbox=[abs_px1, abs_py1, abs_px2, abs_py2], 
                              plate_crop_path=plate_crop_path,
                              latency_ms=(time.perf_counter()-t0)*1000)
            return

        track_id = ev.track_id
        if track_id not in self.consensus_memory:
            self.consensus_memory[track_id] = []
        self.consensus_memory[track_id].append(norm_text)
        
        if len(self.consensus_memory[track_id]) > 5:
            self.consensus_memory[track_id].pop(0)
            
        observations = self.consensus_memory[track_id]
        from collections import Counter
        most_common_text, count = Counter(observations).most_common(1)[0]
        
        self.metrics["ocr_success"] += 1
        
        latency_ms = (time.perf_counter()-t0)*1000
        self.metrics["total_latency_ms"] += latency_ms
        logger.info(f"ANPR_SUCCESS for {ev.event_id}. Plate: {most_common_text} in {latency_ms:.1f}ms")
        
        self._save_result(
            ev, 
            status="SUCCESS",
            raw_text=raw_text,
            norm_text=most_common_text,
            plate_conf=p_conf,
            ocr_conf=ocr_conf,
            plate_bbox=[abs_px1, abs_py1, abs_px2, abs_py2],
            plate_crop_path=plate_crop_path,
            consensus_count=count,
            latency_ms=latency_ms
        )

    def _save_result(self, ev: SecurityEvent, status: str, raw_text: str = None, norm_text: str = None,
                     plate_conf: float = None, ocr_conf: float = None, plate_bbox: List[int] = None,
                     plate_crop_path: str = None,
                     consensus_count: int = 1, latency_ms: float = 0.0):
        
        bbox_str = str(plate_bbox) if plate_bbox else None
        vehicle_class = ev.metadata.get("object_class", "")
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO anpr_reads (
                    event_id, camera_id, track_id, plate_text, confidence, vehicle_class, timestamp, 
                    created_at, plate_text_raw, plate_text_normalized, plate_confidence, ocr_confidence,
                    plate_bbox, plate_crop_path, consensus_count, status, processing_latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ev.event_id, ev.camera_id, ev.track_id, norm_text or "", ocr_conf, vehicle_class, ev.timestamp,
                raw_text, norm_text, plate_conf, ocr_conf, bbox_str, plate_crop_path, consensus_count, status, latency_ms
            ))
            conn.commit()
            
            if status == "SUCCESS":
                self._broadcast_ws(ev, norm_text, ocr_conf)
                
        except Exception as e:
            logger.error(f"Failed to save ANPR result for {ev.event_id}: {e}")

    def _broadcast_ws(self, ev: SecurityEvent, plate_text: str, confidence: float):
        try:
            from app.api.websocket import manager
            import asyncio
            payload = {
                "type": "ANPR_RESULT",
                "data": {
                    "event_id": ev.event_id,
                    "camera_id": ev.camera_id,
                    "track_id": ev.track_id,
                    "vehicle_class": ev.metadata.get("object_class", ""),
                    "plate_text": plate_text,
                    "confidence": confidence,
                    "timestamp": ev.timestamp,
                    "status": "SUCCESS"
                }
            }
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            loop.run_until_complete(manager.broadcast(payload))
        except Exception as e:
            logger.warning(f"Failed to broadcast ANPR WS event: {e}")

    def stop(self):
        self.running = False
        self.queue.put(None)
        self.join(timeout=2.0)

class ANPRService:
    def __init__(self, config: SystemConfiguration, db: SQLiteDatabase):
        self.config = config
        self.db = db
        self.worker = ANPRWorker(config, db)
        self.processed_events = set()
        self.valid_vehicles = {"car", "bike", "motorcycle", "truck", "bus"}

    def start(self):
        if getattr(self.config, "anpr_enabled", True):
            self.worker.start()

    def stop(self):
        self.worker.stop()

    def enqueue_job(self, event: SecurityEvent, frame: Optional[np.ndarray]) -> bool:
        if not getattr(self.config, "anpr_enabled", True):
            return False
            
        if event.event_id in self.processed_events:
            logger.debug(f"ANPR_JOB_DUPLICATE: Skipping duplicate event {event.event_id}")
            return False
            
        obj_class = event.metadata.get("object_class", "").lower()
        if obj_class not in self.valid_vehicles:
            logger.debug(f"ANPR_JOB_SKIPPED_NON_VEHICLE: Skipping class {obj_class}")
            return False

        self.processed_events.add(event.event_id)
        logger.info(f"ANPR_JOB_CREATED for event {event.event_id}")
        req = ANPRRequest(event, frame)
        return self.worker.enqueue(req)
