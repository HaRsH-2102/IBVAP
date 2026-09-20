"""
IBVAP Domain Models — Public Re-exports
========================================
Import domain models from this package for convenience.

Example:
    from app.domain import Camera, Frame, Detection, Track, Event, Alert
"""

from app.domain.alert import Alert, AlertState
from app.domain.camera import Camera, CameraStatus
from app.domain.detection import Detection, BoundingBox, ObjectClass
from app.domain.event import Event, EventStatus, EventType
from app.domain.evidence import EvidencePackage, EvidenceStatus, EvidenceQuality
from app.domain.frame import Frame
from app.domain.risk_assessment import RiskAssessment, SeverityLevel
from app.domain.system_config import SystemConfiguration
from app.domain.track import Track, TrackPoint, TrackState
from app.domain.video_stream import SourceType, StreamState, VideoStream
from app.domain.virtual_line import Direction, VirtualLine
from app.domain.zone import Point, Zone, ZoneType

__all__ = [
    # Camera
    "Camera",
    "CameraStatus",
    # VideoStream
    "VideoStream",
    "StreamState",
    "SourceType",
    # Frame
    "Frame",
    # Detection
    "Detection",
    "BoundingBox",
    "ObjectClass",
    # Track
    "Track",
    "TrackPoint",
    "TrackState",
    # Zone
    "Zone",
    "ZoneType",
    "Point",
    # VirtualLine
    "VirtualLine",
    "Direction",
    # Event
    "Event",
    "EventType",
    "EventStatus",
    # RiskAssessment
    "RiskAssessment",
    "SeverityLevel",
    # Alert
    "Alert",
    "AlertState",
    # Evidence
    "EvidencePackage",
    "EvidenceStatus",
    "EvidenceQuality",
    # SystemConfiguration
    "SystemConfiguration",
]
