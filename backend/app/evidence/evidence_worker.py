import threading
import queue
import time
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import numpy as np
import traceback

from app.domain.evidence import EvidencePackage, EvidenceStatus, EvidenceQuality
from app.domain.security import SecurityEvent
from app.infrastructure.evidence_repository import LocalEvidenceRepository
from app.infrastructure.evidence_storage import EvidenceStorage
from app.evidence.evidence_renderer import EvidenceRenderer
from app.domain.system_config import SystemConfiguration

logger = logging.getLogger("IBVAP.EvidenceWorker")

class EvidenceRequest:
    def __init__(self, 
                 security_event: SecurityEvent, 
                 frame: Optional[np.ndarray], 
                 retries: int = 0,
                 requested_at: Optional[datetime] = None):
        self.security_event = security_event
        self.frame = frame
        self.retries = retries
        self.requested_at = requested_at or datetime.now(timezone.utc)


class EvidenceWorker:
    def __init__(self, 
                 config: SystemConfiguration,
                 repository: LocalEvidenceRepository,
                 storage: EvidenceStorage,
                 renderer: EvidenceRenderer):
        self.config = config
        self.repository = repository
        self.storage = storage
        self.renderer = renderer
        
        self.queue = queue.Queue(maxsize=self.config.evidence_queue_capacity)
        self.is_running = False
        self.thread = None
        
        # Metrics
        self.metrics = {
            "requests_received": 0,
            "requests_processed": 0,
            "queue_failures": 0,
            "storage_failures": 0,
            "max_processing_latency_ms": 0.0,
            "avg_processing_latency_ms": 0.0,
            "missing_frames": 0
        }

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="EvidenceWorker")
        self.thread.start()
        logger.info("EvidenceWorker started")

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info("EvidenceWorker stopped")

    def enqueue(self, request: EvidenceRequest) -> bool:
        if not self.config.evidence_enabled:
            return False
            
        self.metrics["requests_received"] += 1
        try:
            self.queue.put_nowait(request)
            return True
        except queue.Full:
            self.metrics["queue_failures"] += 1
            logger.warning(f"Evidence queue full! Cannot queue evidence for event {request.security_event.event_id}")
            self._handle_queue_full(request)
            return False

    def _handle_queue_full(self, request: EvidenceRequest):
        # Create a QUEUE_FAILED evidence metadata package without frame
        evidence_id = str(uuid.uuid4())
        pkg = EvidencePackage(
            evidence_id=evidence_id,
            security_event_id=request.security_event.event_id,
            alert_id=None,
            camera_id=request.security_event.camera_id,
            track_id=request.security_event.track_id,
            event_type=request.security_event.event_type,
            timestamp=request.security_event.timestamp,
            status=EvidenceStatus.QUEUE_FAILED,
            failure_reason="EVIDENCE_QUEUE_FULL"
        )
        try:
            self.repository.create_evidence(pkg)
        except Exception as e:
            logger.error(f"Failed to persist QUEUE_FAILED evidence for {request.security_event.event_id}: {e}")

    def _worker_loop(self):
        while self.is_running:
            try:
                request = self.queue.get(timeout=1.0)
                self._process_request(request)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Evidence worker unhandled exception: {e}")
                logger.error(traceback.format_exc())

    def _process_request(self, request: EvidenceRequest):
        start_time = time.perf_counter()
        event = request.security_event
        
        # Check idempotency
        existing = self.repository.get_by_security_event_id(event.event_id)
        if existing and existing.status == EvidenceStatus.PERSISTED:
            logger.debug(f"Evidence already persisted for event {event.event_id}")
            return
            
        evidence_id = str(uuid.uuid4())
        date_str = event.timestamp.strftime("%Y-%m-%d")
        
        # 1. Evaluate Evidence Quality
        delta_ms = 0.0
        actual_ts = event.timestamp # Fallback to exact if missing frame ts
        
        if request.frame is None:
            self.metrics["missing_frames"] += 1
            status = EvidenceStatus.UNAVAILABLE
            quality = EvidenceQuality.UNAVAILABLE
        else:
            status = EvidenceStatus.CAPTURED
            quality = EvidenceQuality.EXACT # Assuming realtime for now
            
        pkg = EvidencePackage(
            evidence_id=evidence_id,
            security_event_id=event.event_id,
            camera_id=event.camera_id,
            track_id=event.track_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            requested_event_timestamp=event.timestamp,
            actual_frame_timestamp=actual_ts,
            timestamp_delta_ms=delta_ms,
            evidence_quality=quality,
            status=status,
            metadata=event.metadata
        )

        try:
            if request.frame is not None:
                # 2. Render Annotation
                annotated_frame = self.renderer.render(
                    original_frame=request.frame,
                    bounding_box=event.metadata.get("evidence", {}).get("bounding_box"),
                    event_type=event.event_type,
                    track_id=event.track_id,
                    object_class=event.metadata.get("object_class"),
                    timestamp_str=event.timestamp.isoformat(),
                    camera_id=event.camera_id
                )
                
                # 3. Save Files
                orig_path, annot_path = self.storage.save_evidence_artifacts(
                    camera_id=event.camera_id,
                    date_str=date_str,
                    evidence_id=evidence_id,
                    original_frame=request.frame,
                    annotated_frame=annotated_frame
                )
                
                pkg.original_frame_path = orig_path
                pkg.annotated_frame_reference = annot_path
                pkg.status = EvidenceStatus.PERSISTED
            
            # 4. Commit to DB
            self.repository.create_evidence(pkg)
            
        except Exception as e:
            logger.error(f"Evidence creation failed for event {event.event_id}: {e}")
            self.metrics["storage_failures"] += 1
            pkg.status = EvidenceStatus.STORAGE_FAILED
            pkg.failure_reason = str(e)
            try:
                self.repository.create_evidence(pkg)
            except Exception as db_err:
                logger.error(f"Could not persist failure status to DB: {db_err}")
                
        finally:
            self.metrics["requests_processed"] += 1
            latency = (time.perf_counter() - start_time) * 1000
            self.metrics["avg_processing_latency_ms"] = (self.metrics["avg_processing_latency_ms"] * (self.metrics["requests_processed"] - 1) + latency) / max(1, self.metrics["requests_processed"])
            self.metrics["max_processing_latency_ms"] = max(self.metrics["max_processing_latency_ms"], latency)
