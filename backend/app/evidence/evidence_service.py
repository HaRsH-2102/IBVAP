from typing import Optional
import numpy as np

from app.domain.security import SecurityEvent
from app.domain.system_config import SystemConfiguration
from app.infrastructure.evidence_repository import LocalEvidenceRepository
from app.infrastructure.evidence_storage import EvidenceStorage
from app.evidence.evidence_renderer import EvidenceRenderer
from app.evidence.evidence_worker import EvidenceWorker, EvidenceRequest


class EvidenceService:
    """
    Facade for interacting with the Evidence subsystem.
    Manages the lifecycle of the EvidenceWorker.
    """
    def __init__(self, 
                 config: SystemConfiguration,
                 repository: LocalEvidenceRepository,
                 storage: EvidenceStorage,
                 renderer: EvidenceRenderer):
        self.config = config
        self.repository = repository
        self.worker = EvidenceWorker(config, repository, storage, renderer)

    def start(self):
        if self.config.evidence_enabled:
            self.worker.start()

    def stop(self):
        self.worker.stop()

    def enqueue_evidence(self, event: SecurityEvent, frame: Optional[np.ndarray]) -> bool:
        """
        Asynchronously captures evidence for the provided security event.
        Called by the M6 pipeline on the critical path. Returns immediately.
        """
        if not self.config.evidence_enabled:
            return False
            
        req = EvidenceRequest(security_event=event, frame=frame)
        return self.worker.enqueue(req)

    def get_metrics(self) -> dict:
        return {
            "worker_queue_depth": self.worker.queue.qsize(),
            **self.worker.metrics
        }
