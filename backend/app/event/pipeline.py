import time
import logging
from typing import List, Dict, Tuple, Union
from collections import deque

from app.domain.spatial import SpatialEvent
from app.domain.behavioral import BehavioralEvent
from app.event.normalizer import EventNormalizer
from app.event.rule_engine import RuleEngine
from app.event.correlator import BasicCorrelator
from app.event.alert_manager import AlertManager
from app.infrastructure.repositories import SecurityEventRepository
from app.evidence.evidence_service import EvidenceService

logger = logging.getLogger("IBVAP.EventPipeline")

class M6EventPipeline:
    """
    The orchestrator for the M6 Event Interpretation pipeline.
    Maintains a bounded queue of incoming events and processes them through:
    Normalizer -> RuleEngine -> Correlator -> AlertManager -> Repositories.
    """
    def __init__(self, 
                 rule_engine: RuleEngine, 
                 correlator: BasicCorrelator, 
                 alert_manager: AlertManager,
                 sec_repo: SecurityEventRepository,
                 evidence_service: EvidenceService = None,
                 anpr_service = None,
                 max_queue_size: int = 1000):
        self.normalizer = EventNormalizer()
        self.rule_engine = rule_engine
        self.correlator = correlator
        self.alert_manager = alert_manager
        self.sec_repo = sec_repo
        self.evidence_service = evidence_service
        self.anpr_service = anpr_service
        
        self.queue = deque(maxlen=max_queue_size)
        
        # Metrics
        self.metrics = {
            "events_received": 0,
            "events_processed": 0,
            "malformed_events": 0,
            "security_events_generated": 0,
            "alerts_created": 0,
            "queue_drops": 0, # If we push when full
            "avg_event_processing_ms": 0.0,
            "max_event_processing_ms": 0.0
        }

        # Additional detailed metrics
        self.metrics.update({
            "avg_logic_ms": 0.0,
            "avg_sec_repo_ms": 0.0,
            "avg_alert_manager_ms": 0.0
        })

    def enqueue(self, events: List[Union[SpatialEvent, BehavioralEvent]]):
        for e in events:
            if len(self.queue) == self.queue.maxlen:
                logger.error("M6 Event Queue full! Dropping oldest event.")
                self.metrics["queue_drops"] += 1
            self.queue.append(e)
            self.metrics["events_received"] += 1
            
    def process_all_pending(self, current_frame=None, current_tracks=None):
        """
        Process all pending events in the queue.
        :param current_frame: np.ndarray, the raw image frame for evidence.
        :param current_tracks: list of Track objects, to extract bounding boxes.
        """
        while self.queue:
            raw_event = self.queue.popleft()
            self._process_single(raw_event, current_frame, current_tracks)

    def _update_avg(self, metric_key: str, elapsed_ms: float):
        n = self.metrics["events_processed"]
        # when n is 1, (current*0 + new)/1 = new
        # n is already incremented when we call this for total latency, but let's just do moving avg manually
        if n == 0:
            n = 1
        current_avg = self.metrics[metric_key]
        self.metrics[metric_key] = current_avg + (elapsed_ms - current_avg) / n

    def _process_single(self, raw_event: Union[SpatialEvent, BehavioralEvent], current_frame=None, current_tracks=None):
        start_time = time.perf_counter()
        
        logic_start = time.perf_counter()
        try:
            # 1. Normalize
            event = self.normalizer.normalize(raw_event)
            if not event:
                self.metrics["malformed_events"] += 1
                return
                
            # 2. Rule Engine
            security_events = self.rule_engine.evaluate(event)
            if not security_events:
                return # No rules matched
                
            self.metrics["security_events_generated"] += len(security_events)
            
            # 3. Correlator
            correlated_events = self.correlator.correlate(security_events)
            
            logic_ms = (time.perf_counter() - logic_start) * 1000
            
            # 4. Save Security Events and enqueue Evidence
            sec_repo_start = time.perf_counter()
            for sec_event in correlated_events:
                # If tracks are available, inject bounding box for evidence
                if current_tracks and sec_event.track_id:
                    for t in current_tracks:
                        if t.track_id == sec_event.track_id:
                            if "evidence" not in sec_event.metadata:
                                sec_event.metadata["evidence"] = {}
                            sec_event.metadata["evidence"]["bounding_box"] = {
                                "x1": int(t.bounding_box.left),
                                "y1": int(t.bounding_box.top),
                                "x2": int(t.bounding_box.right),
                                "y2": int(t.bounding_box.bottom)
                            }
                            if "object_class" not in sec_event.metadata:
                                sec_event.metadata["object_class"] = t.object_class.value if hasattr(t.object_class, 'value') else str(t.object_class)
                            break
                            
                self.sec_repo.save(sec_event)
                if self.evidence_service:
                    frame = current_frame
                    if frame is None and hasattr(raw_event, "evidence") and isinstance(raw_event.evidence, dict):
                        frame = raw_event.evidence.get("frame")
                    self.evidence_service.enqueue_evidence(sec_event, frame)
                    
                if self.anpr_service:
                    frame = current_frame
                    if frame is None and hasattr(raw_event, "evidence") and isinstance(raw_event.evidence, dict):
                        frame = raw_event.evidence.get("frame")
                    self.anpr_service.enqueue_job(sec_event, frame)
                    
            sec_repo_ms = (time.perf_counter() - sec_repo_start) * 1000
                
            # 5. Alert Manager (Deduplication and Creation)
            alert_manager_start = time.perf_counter()
            alerts = self.alert_manager.process_events(correlated_events)
            self.metrics["alerts_created"] += len(alerts)
            alert_manager_ms = (time.perf_counter() - alert_manager_start) * 1000
            
        except Exception as e:
            logger.error(f"Pipeline error processing event {raw_event.event_id}: {e}")
            logic_ms, sec_repo_ms, alert_manager_ms = 0, 0, 0
        finally:
            self.metrics["events_processed"] += 1
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Update metrics
            if elapsed_ms > self.metrics["max_event_processing_ms"]:
                self.metrics["max_event_processing_ms"] = elapsed_ms
                
            self._update_avg("avg_event_processing_ms", elapsed_ms)
            if 'logic_ms' in locals():
                self._update_avg("avg_logic_ms", logic_ms)
                self._update_avg("avg_sec_repo_ms", sec_repo_ms)
                self._update_avg("avg_alert_manager_ms", alert_manager_ms)
