"""
IBVAP Backend Tests — Domain Model Validation
===============================================
Tests that all domain models can be instantiated correctly and that
their contracts are well-formed.

These tests validate the Milestone 1 deliverables:
    - Domain model field types
    - Enum values
    - Computed properties
    - Required vs optional fields
    - BoundingBox geometry calculations
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.domain.alert import Alert, AlertState
from app.domain.camera import Camera, CameraStatus
from app.domain.detection import BoundingBox, Detection, ObjectClass
from app.domain.evidence import EvidencePackage, EvidenceStatus, EvidenceQuality
from app.domain.event import Event, EventStatus, EventType
from app.domain.frame import Frame
from app.domain.risk_assessment import RiskAssessment, SeverityLevel
from app.domain.system_config import SystemConfiguration
from app.domain.track import Track, TrackPoint, TrackState
from app.domain.video_stream import SourceType, StreamState, VideoStream
from app.domain.virtual_line import Direction, VirtualLine
from app.domain.zone import Point, Zone, ZoneType


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


def make_bbox(left=10.0, top=20.0, right=110.0, bottom=120.0) -> BoundingBox:
    return BoundingBox(left=left, top=top, right=right, bottom=bottom)


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

class TestCamera:
    def test_minimal_camera(self):
        cam = Camera(camera_id="cam-001", name="North Gate")
        assert cam.camera_id == "cam-001"
        assert cam.name == "North Gate"
        assert cam.status == CameraStatus.UNKNOWN
        assert cam.zone_ids == []
        assert cam.virtual_line_ids == []

    def test_camera_with_all_fields(self):
        cam = Camera(
            camera_id="cam-002",
            name="East Perimeter",
            location="Sector 3",
            status=CameraStatus.ACTIVE,
            capabilities=["infrared", "ptz"],
            zone_ids=["zone-01", "zone-02"],
            virtual_line_ids=["line-01"],
        )
        assert cam.status == CameraStatus.ACTIVE
        assert "infrared" in cam.capabilities
        assert len(cam.zone_ids) == 2

    def test_camera_status_enum_values(self):
        assert set(CameraStatus) == {
            CameraStatus.ACTIVE, CameraStatus.INACTIVE,
            CameraStatus.ERROR, CameraStatus.UNKNOWN,
        }


# ---------------------------------------------------------------------------
# VideoStream
# ---------------------------------------------------------------------------

class TestVideoStream:
    def test_minimal_video_stream(self):
        vs = VideoStream(stream_id="stream-001", camera_id="cam-001")
        assert vs.state == StreamState.CONNECTING
        assert vs.fps == 0.0
        assert vs.error_message is None

    def test_stream_state_enum(self):
        assert StreamState.ACTIVE in set(StreamState)
        assert StreamState.ERROR in set(StreamState)

    def test_source_type_enum(self):
        assert SourceType.RTSP in set(SourceType)
        assert SourceType.FILE in set(SourceType)
        assert SourceType.WEBCAM in set(SourceType)


# ---------------------------------------------------------------------------
# Frame
# ---------------------------------------------------------------------------

class TestFrame:
    def test_minimal_frame(self):
        frame = Frame(
            frame_id="frame-001",
            camera_id="cam-001",
            timestamp=NOW,
        )
        assert frame.frame_id == "frame-001"
        assert frame.camera_id == "cam-001"
        assert frame.data is None  # Data excluded by default

    def test_frame_has_camera_id(self):
        """Every frame must carry camera_id for full data lineage."""
        frame = Frame(frame_id="f-1", camera_id="cam-007", timestamp=NOW)
        assert frame.camera_id == "cam-007"


# ---------------------------------------------------------------------------
# BoundingBox + Detection
# ---------------------------------------------------------------------------

# BoundingBox tests removed because the canonical model only contains data fields.


class TestDetection:
    def test_minimal_detection(self):
        det = Detection(
            detection_id="det-001",
            camera_id="cam-001",
            frame_id="frame-001",
            class_name="person",
            bbox_xyxy=(10.0, 20.0, 110.0, 120.0),
            confidence=0.92,
            timestamp=NOW,
        )
        assert det.detection_id == "det-001"
        assert det.class_name == "person"
        assert det.confidence == 0.92

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            Detection(
                detection_id="det-bad",
                camera_id="cam-001",
                frame_id="frame-001",
                class_name="car",
                bbox_xyxy=(10.0, 20.0, 110.0, 120.0),
                confidence=1.5,  # Invalid — above 1.0
                timestamp=NOW,
            )

    def test_object_class_enum_covers_required_classes(self):
        required = {ObjectClass.PERSON, ObjectClass.CAR, ObjectClass.MOTORCYCLE,
                    ObjectClass.BUS, ObjectClass.TRUCK}
        for req in required:
            assert req in ObjectClass

    def test_detection_carries_camera_id(self):
        det = Detection(
            detection_id="det-002",
            camera_id="cam-999",
            frame_id="f-1",
            class_name="truck",
            bbox_xyxy=(10.0, 20.0, 110.0, 120.0),
            confidence=0.75,
            timestamp=NOW,
        )
        assert det.camera_id == "cam-999"


# ---------------------------------------------------------------------------
# Track
# ---------------------------------------------------------------------------

class TestTrack:
    def test_minimal_track(self):
        track = Track(
            track_id="track-007",
            camera_id="cam-001",
            object_class=ObjectClass.PERSON,
            bounding_box=make_bbox(),
            first_seen=NOW,
            last_seen=NOW,
        )
        assert track.track_id == "track-007"
        assert track.state == TrackState.ACTIVE
        assert track.trajectory == []

    def test_dwell_seconds(self):
        from datetime import timedelta
        first = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        last = datetime(2026, 1, 1, 12, 1, 30, tzinfo=timezone.utc)
        track = Track(
            track_id="t-1",
            camera_id="cam-001",
            object_class=ObjectClass.PERSON,
            bounding_box=make_bbox(),
            first_seen=first,
            last_seen=last,
        )
        assert track.dwell_seconds == 90.0

    def test_track_state_enum(self):
        assert TrackState.ACTIVE in set(TrackState)
        assert TrackState.LOST in set(TrackState)
        assert TrackState.REMOVED in set(TrackState)


# ---------------------------------------------------------------------------
# Zone
# ---------------------------------------------------------------------------

class TestZone:
    def test_minimal_zone(self):
        zone = Zone(zone_id="zone-01", camera_id="cam-001", name="Restricted Zone A")
        assert zone.zone_type == ZoneType.NORMAL
        assert zone.active is True

    def test_polygon_validity(self):
        zone_valid = Zone(
            zone_id="z-1",
            camera_id="cam-001",
            name="Valid Zone",
            geometry=[Point(x=0, y=0), Point(x=100, y=0), Point(x=50, y=100)],
        )
        assert zone_valid.is_valid_polygon() is True

    def test_polygon_invalid_too_few_points(self):
        zone_invalid = Zone(
            zone_id="z-2",
            camera_id="cam-001",
            name="Invalid Zone",
            geometry=[Point(x=0, y=0), Point(x=100, y=0)],  # Only 2 points
        )
        assert zone_invalid.is_valid_polygon() is False

    def test_zone_type_enum(self):
        assert ZoneType.RESTRICTED in set(ZoneType)
        assert ZoneType.MONITORING in set(ZoneType)


# ---------------------------------------------------------------------------
# VirtualLine
# ---------------------------------------------------------------------------

class TestVirtualLine:
    def test_minimal_virtual_line(self):
        line = VirtualLine(
            line_id="line-01",
            camera_id="cam-001",
            name="Entry Boundary",
            start=Point(x=0, y=300),
            end=Point(x=1920, y=300),
        )
        assert line.allowed_direction == Direction.BOTH
        assert line.active is True

    def test_direction_enum(self):
        assert Direction.A_TO_B in set(Direction)
        assert Direction.B_TO_A in set(Direction)
        assert Direction.NONE in set(Direction)


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class TestEvent:
    def test_minimal_event(self):
        event = Event(
            event_id="evt-001",
            camera_id="cam-001",
            event_type=EventType.INTRUSION,
            timestamp=NOW,
        )
        assert event.event_type == EventType.INTRUSION
        assert event.status == EventStatus.OPEN
        assert event.evidence_ids == []

    def test_event_type_enum_coverage(self):
        required = {
            EventType.INTRUSION, EventType.LOITERING, EventType.LINE_CROSSING,
            EventType.NIGHT_MOVEMENT, EventType.VEHICLE_INTRUSION,
            EventType.ANPR_DETECTION, EventType.FACE_DETECTION,
        }
        assert required.issubset(set(EventType))


# ---------------------------------------------------------------------------
# RiskAssessment
# ---------------------------------------------------------------------------

class TestRiskAssessment:
    def test_minimal_risk_assessment(self):
        ra = RiskAssessment(
            assessment_id="ra-001",
            event_id="evt-001",
        )
        assert ra.risk_score == 0.0
        assert ra.severity == SeverityLevel.LOW

    def test_severity_enum(self):
        assert SeverityLevel.CRITICAL in set(SeverityLevel)
        assert SeverityLevel.HIGH in set(SeverityLevel)

    def test_risk_score_bounds(self):
        with pytest.raises(Exception):
            RiskAssessment(assessment_id="ra-bad", event_id="e-1", risk_score=150.0)


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

class TestAlert:
    def test_minimal_alert(self):
        alert = Alert(
            alert_id="alert-001",
            event_id="evt-001",
            severity=SeverityLevel.HIGH,
            created_at=NOW,
        )
        assert alert.state == AlertState.DETECTED
        assert alert.acknowledged_at is None
        assert alert.resolved_at is None

    def test_alert_state_lifecycle(self):
        states = set(AlertState)
        expected = {
            AlertState.DETECTED, AlertState.ACTIVE,
            AlertState.ACKNOWLEDGED, AlertState.INVESTIGATING,
            AlertState.RESOLVED, AlertState.SUPPRESSED,
        }
        assert expected == states


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class TestEvidence:
    def test_evidence_model_creation(self):
        evidence = EvidencePackage(
            evidence_id="ev-001",
            security_event_id="evt-001",
            camera_id="cam-001",
            event_type="LOITERING",
            timestamp=datetime.now(timezone.utc),
            status=EvidenceStatus.PENDING
        )
        assert evidence.evidence_id == "ev-001"
        assert evidence.security_event_id == "evt-001"
        assert evidence.camera_id == "cam-001"
        assert evidence.status == EvidenceStatus.PENDING

    def test_evidence_enums(self):
        assert EvidenceStatus.PENDING in set(EvidenceStatus)
        assert EvidenceQuality.EXACT in set(EvidenceQuality)


# ---------------------------------------------------------------------------
# SystemConfiguration
# ---------------------------------------------------------------------------

class TestSystemConfiguration:
    def test_defaults(self):
        config = SystemConfiguration()
        assert config.log_level == "INFO"
        assert config.max_cameras == 16
        assert 0.0 < config.default_confidence_threshold < 1.0

    def test_from_settings(self):
        """Verify the factory method works with mock settings."""
        class MockSettings:
            log_level = "DEBUG"
            api_version = "v1"
            storage_base_path = "./test_storage"
            evidence_retention_days = 7
            default_confidence_threshold = 0.6
            loitering_threshold_seconds = 30
            night_start_hour = 22
            night_end_hour = 5
            max_cameras = 4
            processing_fps_limit = 15

        config = SystemConfiguration.from_settings(MockSettings())
        assert config.log_level == "DEBUG"
        assert config.max_cameras == 4
        assert config.night_start_hour == 22
