import threading
import queue
import time
import uuid
import logging
import os
import shutil
import cv2
import traceback
from typing import Optional, Dict
from datetime import datetime, timezone, timedelta

from app.domain.incident_clip import IncidentClip, ClipStatus
from app.domain.evidence import EvidencePackage
from app.domain.security import SecurityEvent
from app.domain.system_config import SystemConfiguration
from app.infrastructure.clip_repository import SQLiteClipRepository
from app.evidence.evidence_renderer import EvidenceRenderer

logger = logging.getLogger("IBVAP.ClipWorker")

class ClipRequest:
    def __init__(self,
                 security_event: SecurityEvent,
                 evidence_package: EvidencePackage,
                 source_video_reference: str,
                 retries: int = 0):
        self.security_event = security_event
        self.evidence_package = evidence_package
        self.source_video_reference = source_video_reference
        self.retries = retries
        self.requested_at = datetime.now(timezone.utc)

class ClipWorker:
    def __init__(self,
                 config: SystemConfiguration,
                 repository: SQLiteClipRepository,
                 renderer: EvidenceRenderer):
        self.config = config
        self.repository = repository
        self.renderer = renderer
        
        self.queue = queue.Queue(maxsize=self.config.clip_queue_capacity)
        self.is_running = False
        self.thread = None
        
        # Check encoder capabilities
        self.encoder_available = self._check_encoder()
        if not self.encoder_available:
            logger.error("MP4 encoder (mp4v) is not available. ClipWorker will fail all requests.")

    def _check_encoder(self) -> bool:
        """Verify the configured video encoder is available."""
        # A quick check by trying to initialize a tiny dummy VideoWriter
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            dummy_path = os.path.join(self.config.storage_base_path, "dummy_test.mp4")
            os.makedirs(self.config.storage_base_path, exist_ok=True)
            writer = cv2.VideoWriter(dummy_path, fourcc, 1.0, (10, 10))
            if not writer.isOpened():
                return False
            writer.release()
            if os.path.exists(dummy_path):
                os.remove(dummy_path)
            return True
        except Exception:
            return False

    def _check_disk_space(self) -> bool:
        """Enforce disk backpressure."""
        try:
            total, used, free = shutil.disk_usage(self.config.storage_base_path)
            free_gb = free / (2**30)
            return free_gb >= self.config.minimum_free_disk_gb
        except Exception:
            # If we can't check, assume it's fine for now, or fail safe. We assume fine.
            return True

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="ClipWorker")
        self.thread.start()
        logger.info("ClipWorker started")

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info("ClipWorker stopped")

    def enqueue(self, request: ClipRequest) -> bool:
        if not self.config.incident_clip_enabled:
            return False
            
        try:
            self.queue.put_nowait(request)
            return True
        except queue.Full:
            logger.warning(f"Clip queue full! Cannot queue clip for event {request.security_event.event_id}")
            self._handle_queue_full(request)
            return False

    def _handle_queue_full(self, request: ClipRequest):
        if request.retries < self.config.max_clip_retries:
            # Requeue later or handle backoff in a more sophisticated system
            # For simplicity in this bounded queue, we fail it.
            pass
            
        clip = IncidentClip(
            clip_id=str(uuid.uuid4()),
            security_event_id=request.security_event.event_id,
            camera_id=request.security_event.camera_id,
            event_type=request.security_event.event_type,
            event_timestamp=request.security_event.timestamp,
            status=ClipStatus.FAILED,
            failure_reason="CLIP_QUEUE_FULL"
        )
        self.repository.create_clip(clip)

    def _worker_loop(self):
        while self.is_running:
            try:
                request = self.queue.get(timeout=1.0)
                self._process_request(request)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Clip worker unhandled exception: {e}")
                logger.error(traceback.format_exc())

    def _process_request(self, request: ClipRequest):
        event = request.security_event
        evidence = request.evidence_package
        
        # Idempotency check
        existing = self.repository.get_by_security_event_id(event.event_id)
        if existing and existing.status == ClipStatus.PERSISTED:
            logger.debug(f"Clip already persisted for event {event.event_id}")
            return
            
        clip_id = existing.clip_id if existing else str(uuid.uuid4())
        
        clip = IncidentClip(
            clip_id=clip_id,
            security_event_id=event.event_id,
            camera_id=event.camera_id,
            event_type=event.event_type,
            event_timestamp=event.timestamp,
            alert_id=evidence.alert_id,
            evidence_id=evidence.evidence_id,
            track_id=event.track_id,
            source_video_reference=request.source_video_reference,
            status=ClipStatus.CAPTURING
        )
        
        if not existing:
            self.repository.create_clip(clip)
            
        if not self.encoder_available:
            clip.status = ClipStatus.FAILED
            clip.failure_reason = "ENCODER_UNAVAILABLE"
            self.repository.update_clip(clip)
            return
            
        if not self._check_disk_space():
            clip.status = ClipStatus.FAILED
            clip.failure_reason = "INSUFFICIENT_DISK_SPACE"
            self.repository.update_clip(clip)
            return

        try:
            self._generate_clip(clip, request)
        except Exception as e:
            logger.error(f"Failed to generate clip for event {event.event_id}: {e}")
            clip.status = ClipStatus.FAILED
            clip.failure_reason = str(e)
            
            # Simple retry mechanism
            if request.retries < self.config.max_clip_retries:
                logger.info(f"Retrying clip generation for event {event.event_id}")
                request.retries += 1
                self.repository.update_clip(clip)
                time.sleep(2) # Configurable backoff
                self.enqueue(request)
            else:
                self.repository.update_clip(clip)

    def _generate_clip(self, clip: IncidentClip, request: ClipRequest):
        cap = cv2.VideoCapture(request.source_video_reference)
        if not cap.isOpened():
            clip.status = ClipStatus.SOURCE_UNAVAILABLE
            clip.failure_reason = "SOURCE_NOT_FOUND"
            self.repository.update_clip(clip)
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        
        if fps <= 0: fps = 25.0
        
        # Calculate target frame based on event timestamp.
        # This is an approximation for testing. In reality, we'd need exact PTS mapping.
        # Here we assume the video starts at time 0 and event_timestamp is relative, 
        # or we just grab the center if it's a test file.
        # For our synthetic tests and demo, we'll assume the video plays in real-time
        # from the moment ingestion starts, OR we just seek to a relative timestamp.
        # Since SecurityEvent timestamp is absolute UTC, we need a way to map it.
        # Let's extract metadata if the ingestion passed 'frame_ms' or 'frame_index'.
        frame_idx = request.security_event.metadata.get("frame_index")
        
        if frame_idx is None:
            # Fallback: just read the first few seconds if we don't have a mapping
            frame_idx = fps * self.config.pre_event_seconds
            
        pre_frames = int(fps * self.config.pre_event_seconds)
        post_frames = int(fps * self.config.post_event_seconds)
        
        requested_start = frame_idx - pre_frames
        requested_end = frame_idx + post_frames
        
        start_frame = max(0, requested_start)
        end_frame = min(total_frames - 1, requested_end)
        
        if requested_start < 0 or requested_end >= total_frames:
            clip.status = ClipStatus.PARTIAL
        else:
            clip.status = ClipStatus.ENCODING
            
        # We need to save under evidence/<camera_id>/<date>/<evidence_id>/incident_clip.mp4
        date_str = clip.event_timestamp.strftime("%Y-%m-%d")
        evidence_dir = os.path.join(self.config.storage_base_path, "evidence", clip.camera_id, date_str, request.evidence_package.evidence_id)
        os.makedirs(evidence_dir, exist_ok=True)
        
        clip_path = os.path.join(evidence_dir, "incident_clip.mp4")
        thumb_path = os.path.join(evidence_dir, "thumbnail.jpg")
        
        # Setup Video Writer
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*self.config.clip_format.lower() + 'v') # e.g., mp4v
        out = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        current_frame = start_frame
        saved_thumbnail = False
        
        # Bounding box extraction
        static_bbox = request.security_event.metadata.get("evidence", {}).get("bounding_box", None)
        obj_class = request.security_event.metadata.get("object_class")
        
        # Build trajectory map if available
        trajectory_map = {}
        trajectory_list = request.security_event.metadata.get("trajectory") or \
                          (request.evidence_package.trajectory_snapshot if request.evidence_package else None)
        
        if trajectory_list and isinstance(trajectory_list, list):
            for pt in trajectory_list:
                f_idx = pt.get("frame_index")
                box = pt.get("bounding_box")
                if f_idx is not None and box is not None:
                    trajectory_map[int(f_idx)] = box
        
        while current_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Determine bounding box for current frame
            # If we have dynamic trajectory, use it. If not, only draw static box on the exact event frame.
            current_bbox = None
            if trajectory_map:
                current_bbox = trajectory_map.get(int(current_frame), None)
            else:
                # If no trajectory provided, ONLY draw the static box on the exact event frame to prevent freeze-frame burning
                if int(current_frame) == int(frame_idx):
                    current_bbox = static_bbox
                
            # Annotation
            annotated_frame = self.renderer.render(
                original_frame=frame,
                bounding_box=current_bbox,
                event_type=clip.event_type,
                track_id=clip.track_id,
                object_class=obj_class,
                timestamp_str=clip.event_timestamp.isoformat(),
                camera_id=clip.camera_id
            )
            
            # Event Marker
            if current_frame == int(frame_idx) or (current_frame == start_frame and int(frame_idx) < start_frame):
                cv2.putText(annotated_frame, f"EVENT @ {clip.event_timestamp.strftime('%H:%M:%S.%f')[:-3]}", 
                            (50, height - 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                if self.config.thumbnail_enabled and not saved_thumbnail:
                    cv2.imwrite(thumb_path, annotated_frame)
                    saved_thumbnail = True
                    
            out.write(annotated_frame)
            current_frame += 1
            
        cap.release()
        out.release()
        
        if not saved_thumbnail and self.config.thumbnail_enabled:
            # Fallback thumbnail
            cap = cv2.VideoCapture(clip_path)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(thumb_path, frame)
            cap.release()
            
        clip.clip_path = clip_path
        clip.thumbnail_path = thumb_path
        clip.status = ClipStatus.PERSISTED if clip.status != ClipStatus.PARTIAL else ClipStatus.PARTIAL
        clip.duration_seconds = (current_frame - start_frame) / fps if fps > 0 else 0
        clip.metadata["source_fps"] = fps
        clip.metadata["start_frame"] = start_frame
        clip.metadata["end_frame"] = end_frame
        
        self.repository.update_clip(clip)
