from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime

from app.domain.rule import Severity, AlertStatus

@dataclass
class SecurityEvent:
    event_id: str
    event_type: str
    severity: Severity
    camera_id: str
    track_id: str
    source_spatial_event_id: str
    rule_id: str
    timestamp: datetime
    status: str = "PROCESSED"
    description: str = ""
    metadata: Dict = field(default_factory=dict)
    correlation_id: Optional[str] = None

@dataclass
class Alert:
    alert_id: str
    security_event_ids: List[str]
    camera_id: str
    track_id: str
    rule_id: str
    spatial_object_id: str
    event_type: str
    severity: Severity
    created_at: datetime
    updated_at: datetime
    status: AlertStatus
    title: str
    description: str
    correlation_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    resolved_at: Optional[datetime] = None

@dataclass
class EvidencePackage:
    evidence_id: str
    event_id: str
    camera_id: str
    track_id: str
    frame_id: str
    timestamp: datetime
    event_type: str
    object_class: str
    bbox: Dict[str, float]
    crop_path: str
    full_frame_path: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_saved: bool
    saved_at: Optional[datetime]
