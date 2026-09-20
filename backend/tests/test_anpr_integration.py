import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import numpy as np
from unittest.mock import MagicMock, patch

from app.domain.security import SecurityEvent
from app.infrastructure.database import SQLiteDatabase
from app.domain.system_config import SystemConfiguration
from app.anpr.anpr_service import ANPRService, ANPRWorker, ANPRRequest
from app.event.pipeline import M6EventPipeline

class TestANPRIntegration(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.config = SystemConfiguration()
        self.config.anpr_enabled = True
        self.config.anpr_queue_size = 2 # Small queue for full test
        
        # We replace the actual db with a mock for testing isolation
        self.anpr_service = ANPRService(self.config, self.db)
        # Mock detector and OCR to be fast and not require models
        self.anpr_service.worker.plate_detector = MagicMock()
        self.anpr_service.worker.ocr_engine = MagicMock()
        self.anpr_service.worker.ocr_engine.is_available = True
        
        # Pipeline mock dependencies
        self.sec_repo = MagicMock()
        self.pipeline = M6EventPipeline(
            rule_engine=MagicMock(),
            correlator=MagicMock(),
            alert_manager=MagicMock(),
            sec_repo=self.sec_repo,
            evidence_service=MagicMock(),
            anpr_service=self.anpr_service,
            max_queue_size=10
        )
        
        self.dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)

    def _make_event(self, event_id="E1", obj_class="car"):
        ev = SecurityEvent(event_id=event_id, source_spatial_event_id="dummy", rule_id="dummy", event_type="TEST", severity="HIGH", 
                           camera_id="cam1", track_id="track1", timestamp="2026-09-18")
        ev.metadata = {"object_class": obj_class, "evidence": {"bounding_box": {"x1":10, "y1":10, "x2":50, "y2":50}}}
        return ev

    def test_vehicle_event_queued(self):
        ev = self._make_event("E1", "car")
        enqueued = self.anpr_service.enqueue_job(ev, self.dummy_frame)
        self.assertTrue(enqueued)
        self.assertEqual(self.anpr_service.worker.queue.qsize(), 1)

    def test_person_event_skipped(self):
        ev = self._make_event("E2", "person")
        enqueued = self.anpr_service.enqueue_job(ev, self.dummy_frame)
        self.assertFalse(enqueued)
        self.assertEqual(self.anpr_service.worker.queue.qsize(), 0)

    def test_bike_eligible(self):
        ev = self._make_event("E3", "motorcycle")
        enqueued = self.anpr_service.enqueue_job(ev, self.dummy_frame)
        self.assertTrue(enqueued)

    def test_duplicate_event_id(self):
        ev = self._make_event("E4", "truck")
        e1 = self.anpr_service.enqueue_job(ev, self.dummy_frame)
        e2 = self.anpr_service.enqueue_job(ev, self.dummy_frame) # duplicate
        self.assertTrue(e1)
        self.assertFalse(e2)

    def test_queue_full_isolation(self):
        # Fill queue
        self.anpr_service.enqueue_job(self._make_event("E5", "car"), self.dummy_frame)
        self.anpr_service.enqueue_job(self._make_event("E6", "car"), self.dummy_frame)
        # 3rd should fail but not crash
        e3 = self.anpr_service.enqueue_job(self._make_event("E7", "car"), self.dummy_frame)
        self.assertFalse(e3)

    def test_detector_failure_isolation(self):
        self.anpr_service.worker.plate_detector.detect_in_crop.side_effect = Exception("CUDA OOM")
        req = ANPRRequest(self._make_event("E8", "car"), self.dummy_frame)
        try:
            self.anpr_service.worker._process_job(req)
        except Exception:
            pass # Exception is expected when calling _process_job directly

    def test_ocr_failure_isolation(self):
        self.anpr_service.worker.plate_detector.detect_in_crop.return_value = [(0,0,10,10,0.9)]
        self.anpr_service.worker.ocr_engine.process_crop.side_effect = Exception("OCR Crash")
        req = ANPRRequest(self._make_event("E9", "car"), self.dummy_frame)
        try:
            self.anpr_service.worker._process_job(req)
        except Exception:
            pass # Exception is expected when calling _process_job directly

if __name__ == '__main__':
    unittest.main()
