from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
import uuid

class ClipStatus(Enum):
    REQUESTED = "REQUESTED"
    QUEUED = "QUEUED"
    CAPTURING = "CAPTURING"
    ENCODING = "ENCODING"
    PERSISTED = "PERSISTED"
    FAILED = "FAILED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    PARTIAL = "PARTIAL"

@dataclass
class IncidentClip:
    clip_id: str
    security_event_id: str
    camera_id: str
    event_type: str
    event_timestamp: datetime
    
    alert_id: Optional[str] = None
    evidence_id: Optional[str] = None
    track_id: Optional[str] = None
    
    clip_start_timestamp: Optional[datetime] = None
    clip_end_timestamp: Optional[datetime] = None
    
    pre_event_seconds: Optional[float] = None
    post_event_seconds: Optional[float] = None
    duration_seconds: Optional[float] = None
    
    source_video_reference: Optional[str] = None
    clip_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    
    status: ClipStatus = ClipStatus.REQUESTED
    failure_reason: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
