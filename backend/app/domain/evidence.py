"""
IBVAP Domain — Evidence
========================
Represents supporting material captured in association with a security Event.
Conforms strictly to M10 Evidence & Event Intelligence specifications.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceStatus(str, Enum):
    PENDING = "PENDING"
    CAPTURED = "CAPTURED"
    PERSISTED = "PERSISTED"
    QUEUE_FAILED = "QUEUE_FAILED"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    STORAGE_FAILED = "STORAGE_FAILED"
    ARTIFACT_MISSING = "ARTIFACT_MISSING"
    UNAVAILABLE = "UNAVAILABLE"
    ORPHANED_ARTIFACT = "ORPHANED_ARTIFACT"


class EvidenceQuality(str, Enum):
    EXACT = "EXACT"
    NEAREST_AVAILABLE = "NEAREST_AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class EvidencePackage(BaseModel):
    """
    EvidencePackage as required by M10.
    Stores metadata related to a captured SecurityEvent and pointers to visual artifacts.
    """
    evidence_id: str = Field(..., description="Unique evidence identifier (UUID4)")
    security_event_id: str = Field(..., description="The originating SecurityEvent (Unique constraint)")
    alert_id: Optional[str] = Field(default=None, description="The alert this event triggered")
    camera_id: str = Field(..., description="Source camera identifier")
    track_id: Optional[str] = Field(default=None, description="Tracked object ID")
    event_type: str = Field(..., description="Type of the security event")
    timestamp: datetime = Field(..., description="UTC time of the event")
    object_class: Optional[str] = Field(default=None, description="Class of the tracked object")
    bounding_box: Optional[Dict[str, int]] = Field(default=None, description="Snapshot bounding box dict {x1,y1,x2,y2}")
    scene_state: Optional[str] = Field(default=None, description="Scene state from M8 (e.g. DAY, NIGHT)")
    spatial_context: Optional[Dict[str, Any]] = Field(default=None, description="Zone/Line metadata")
    behavioral_context: Optional[Dict[str, Any]] = Field(default=None, description="Behavioral metadata")
    trajectory_snapshot: Optional[List[Dict[str, Any]]] = Field(default=None, description="Recent N trajectory points")
    
    # Artifact paths
    original_frame_path: Optional[str] = Field(default=None, description="Path to immutable original frame")
    annotated_frame_reference: Optional[str] = Field(default=None, description="Path to annotated frame")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible metadata")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    status: EvidenceStatus = Field(default=EvidenceStatus.PENDING, description="Current lifecycle status")
    
    # Evidence specific timing details
    requested_event_timestamp: Optional[datetime] = None
    actual_frame_timestamp: Optional[datetime] = None
    timestamp_delta_ms: Optional[float] = None
    evidence_quality: Optional[EvidenceQuality] = None
    failure_reason: Optional[str] = None
