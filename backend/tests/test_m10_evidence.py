import unittest
import tempfile
import os
import shutil
import time
from datetime import datetime, timezone
import uuid
import numpy as np

from app.domain.evidence import EvidencePackage, EvidenceStatus, EvidenceQuality
from app.domain.security import SecurityEvent
from app.domain.rule import Severity
from app.domain.system_config import SystemConfiguration
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.evidence_repository import LocalEvidenceRepository
from app.infrastructure.evidence_storage import EvidenceStorage
from app.evidence.evidence_renderer import EvidenceRenderer
from app.evidence.evidence_worker import EvidenceWorker, EvidenceRequest

class TestM10Evidence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_m10.db")
        self.db = SQLiteDatabase(self.db_path)
        self.repo = LocalEvidenceRepository(self.db)
        
        self.config = SystemConfiguration(storage_base_path=self.temp_dir, evidence_queue_capacity=2)
        self.storage = EvidenceStorage(self.config)
        self.renderer = EvidenceRenderer()
        
    def tearDown(self):
        # Force garbage collection to help release SQLite handles before rmtree
        import gc; gc.collect()
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_a_evidence_domain(self):
        # Test A: Evidence Domain
        pkg = EvidencePackage(
            evidence_id="123",
            security_event_id="sec-1",
            camera_id="cam-1",
            event_type="LOITERING",
            timestamp=datetime.now(timezone.utc)
        )
        self.assertEqual(pkg.status, EvidenceStatus.PENDING)
        self.assertIsNone(pkg.track_id)
        
    def test_b_frame_capture_and_persistence(self):
        # Test B & D & E: Frame Capture, Persistence, Annotation
        worker = EvidenceWorker(self.config, self.repo, self.storage, self.renderer)
        worker.start()
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        event = SecurityEvent(
            event_id="sec-2",
            event_type="ZONE_ENTER",
            severity=Severity.HIGH,
            camera_id="cam-1",
            track_id="trk-1",
            source_spatial_event_id="sp-1",
            rule_id="rule-1",
            timestamp=datetime.now(timezone.utc),
            metadata={"evidence": {"bounding_box": {"x1": 10, "y1": 10, "x2": 50, "y2": 50}}, "object_class": "person"}
        )
        
        worker.enqueue(EvidenceRequest(event, frame))
        time.sleep(1.0) # Wait for processing
        
        saved = self.repo.get_by_security_event_id("sec-2")
        self.assertIsNotNone(saved)
        self.assertEqual(saved.status, EvidenceStatus.PERSISTED)
        self.assertTrue(os.path.exists(saved.original_frame_path))
        self.assertTrue(os.path.exists(saved.annotated_frame_reference))
        worker.stop()

    def test_i_queue_full(self):
        # Test I: Queue Full Behavior
        self.config.evidence_queue_capacity = 1 # Very small
        worker = EvidenceWorker(self.config, self.repo, self.storage, self.renderer)
        
        # Don't start worker, just stuff the queue
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        
        # 1st should succeed
        ev1 = SecurityEvent(event_id="sec-q1", event_type="TEST", severity=Severity.LOW, camera_id="c1", track_id="t1", source_spatial_event_id="s1", rule_id="r1", timestamp=datetime.now(timezone.utc))
        success1 = worker.enqueue(EvidenceRequest(ev1, frame))
        self.assertTrue(success1)
        
        # 2nd should fail due to queue full
        ev2 = SecurityEvent(event_id="sec-q2", event_type="TEST", severity=Severity.LOW, camera_id="c1", track_id="t1", source_spatial_event_id="s2", rule_id="r1", timestamp=datetime.now(timezone.utc))
        success2 = worker.enqueue(EvidenceRequest(ev2, frame))
        self.assertFalse(success2)
        
        # Verify failure reason is recorded in DB directly by handle_queue_full
        saved2 = self.repo.get_by_security_event_id("sec-q2")
        self.assertIsNotNone(saved2)
        self.assertEqual(saved2.status, EvidenceStatus.QUEUE_FAILED)
        self.assertEqual(saved2.failure_reason, "EVIDENCE_QUEUE_FULL")

    def test_m_idempotency(self):
        # Test M: Idempotency uniqueness
        pkg1 = EvidencePackage(
            evidence_id="1", security_event_id="sec-unique", camera_id="c", event_type="T", timestamp=datetime.now(timezone.utc)
        )
        pkg2 = EvidencePackage(
            evidence_id="2", security_event_id="sec-unique", camera_id="c", event_type="T", timestamp=datetime.now(timezone.utc)
        )
        
        self.repo.create_evidence(pkg1)
        with self.assertRaises(Exception):
            self.repo.create_evidence(pkg2)

if __name__ == "__main__":
    unittest.main()
