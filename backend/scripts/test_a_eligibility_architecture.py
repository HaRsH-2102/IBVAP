"""
IBVAP ANPR — TEST A: Eligibility Architecture
=============================================

Unit tests the purely architectural filtering mechanisms:
- is_anpr_eligible
- ANPRBenchmarkQueue

Validates the 10 core scenarios using synthetic events.
"""

import asyncio
from datetime import datetime
import uuid

from app.domain.security import SecurityEvent, EvidencePackage
from app.domain.rule import Severity
from app.anpr.benchmark_architecture import is_anpr_eligible, ANPRBenchmarkQueue

def create_mock_event(event_type="Loitering", status="PROCESSED", event_id=None) -> SecurityEvent:
    return SecurityEvent(
        event_id=event_id or str(uuid.uuid4()),
        event_type=event_type,
        severity=Severity.HIGH,
        camera_id="cam_test_01",
        track_id="trk_123",
        source_spatial_event_id="sp_123",
        rule_id="rule_01",
        timestamp=datetime.now(),
        status=status
    )

def create_mock_evidence(obj_class="car", has_crop=True) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=str(uuid.uuid4()),
        event_id="evt_123",
        camera_id="cam_test_01",
        track_id="trk_123",
        frame_id="frm_1",
        timestamp=datetime.now(),
        event_type="Loitering",
        object_class=obj_class,
        bbox={"left": 10, "top": 10, "right": 100, "bottom": 100},
        crop_path="/tmp/crop.jpg" if has_crop else "",
        full_frame_path="/tmp/full.jpg",
        created_at=datetime.now(),
        expires_at=None,
        is_saved=True,
        saved_at=datetime.now()
    )


async def run_test_a():
    print("=======================================")
    print(" TEST A: Eligibility Architecture      ")
    print("=======================================\n")

    passed = 0
    total = 0

    def assert_test(name, result, expected):
        nonlocal passed, total
        total += 1
        if result == expected:
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name} (Expected {expected}, got {result})")

    # 1. PERSON
    evt = create_mock_event()
    evd = create_mock_evidence(obj_class="person")
    assert_test("PERSON -> rejected", is_anpr_eligible(evt, evd), False)

    # 2. CAR
    evt = create_mock_event()
    evd = create_mock_evidence(obj_class="car")
    assert_test("CAR -> accepted", is_anpr_eligible(evt, evd), True)

    # 3. TRUCK
    evt = create_mock_event()
    evd = create_mock_evidence(obj_class="truck")
    assert_test("TRUCK -> accepted", is_anpr_eligible(evt, evd), True)

    # 4. BUS
    evt = create_mock_event()
    evd = create_mock_evidence(obj_class="bus")
    assert_test("BUS -> accepted", is_anpr_eligible(evt, evd), True)

    # 5. MOTORCYCLE
    evt = create_mock_event()
    evd = create_mock_evidence(obj_class="motorcycle")
    assert_test("MOTORCYCLE -> accepted", is_anpr_eligible(evt, evd), True)

    # 6. BICYCLE
    evt = create_mock_event()
    evd = create_mock_evidence(obj_class="bicycle")
    assert_test("BICYCLE -> accepted", is_anpr_eligible(evt, evd), True)

    # 7. NO EVENT (None)
    evd = create_mock_evidence(obj_class="car")
    assert_test("NO EVENT -> rejected", is_anpr_eligible(None, evd), False)

    # 8. UNREGISTERED EVENT
    evt = create_mock_event(status="FAILED")
    evd = create_mock_evidence(obj_class="car")
    assert_test("UNREGISTERED EVENT (FAILED) -> rejected", is_anpr_eligible(evt, evd), False)

    # 9. MISSING CROP
    evt = create_mock_event()
    evd = create_mock_evidence(obj_class="car", has_crop=False)
    assert_test("MISSING CROP -> rejected", is_anpr_eligible(evt, evd), False)

    print("\n--- Queue & Deduplication Tests ---")
    
    queue = ANPRBenchmarkQueue()
    
    # Setup dup event
    dup_evt = create_mock_event(event_id="event_999")
    dup_evd = create_mock_evidence(obj_class="car")
    
    res1 = queue.submit_event(dup_evt, dup_evd)
    assert_test("Duplicate Event (First Submission) -> queued", res1, True)
    
    res2 = queue.submit_event(dup_evt, dup_evd)
    assert_test("Duplicate Event (Second Submission) -> rejected", res2, False)
    
    print(f"\nTotal: {total}, Passed: {passed}")
    assert passed == total, "Some architectural tests failed!"
    print("\nTest A completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_test_a())
