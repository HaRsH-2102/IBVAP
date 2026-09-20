"""
IBVAP Domain — Spatial Models
=============================
Defines the spatial events and configuration models for Milestone 5.
"""

from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.domain.zone import Zone, Point
from app.domain.virtual_line import VirtualLine

class SpatialEventType(str, Enum):
    """
    Events produced by the SpatialEngine based on geometric facts.
    These are purely spatial facts, NOT security alerts.
    """
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    LINE_CROSS = "LINE_CROSS"

class SpatialEvent(BaseModel):
    """
    Represents a geometric fact derived by the Spatial Engine.
    
    Attributes:
        event_id: Unique identifier for this spatial event.
        camera_id: The camera context.
        track_id: The M4 Track ID that triggered the event.
        event_type: ZONE_ENTER, ZONE_EXIT, or LINE_CROSS.
        spatial_object_id: The ID of the Zone or VirtualLine involved.
        timestamp: When the event occurred.
        reference_point: The (x, y) coordinate that triggered the event.
        metadata: Extensible data (e.g. crossing direction).
    """
    event_id: str = Field(..., description="Unique event identifier")
    camera_id: str = Field(..., description="Camera identifier")
    track_id: str = Field(..., description="The tracked object ID")
    event_type: SpatialEventType = Field(..., description="Type of spatial interaction")
    spatial_object_id: str = Field(..., description="Zone ID or VirtualLine ID")
    timestamp: datetime = Field(..., description="UTC time of the event")
    reference_point: Point = Field(..., description="The reference point that triggered this event")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context (e.g., crossing direction)")

class CameraSpatialConfig(BaseModel):
    """
    Configuration grouping all spatial objects for a specific camera.
    """
    camera_id: str = Field(..., description="The camera this configuration applies to")
    zones: List[Zone] = Field(default_factory=list, description="Zones configured for this camera")
    tripwires: List[VirtualLine] = Field(default_factory=list, description="Tripwires configured for this camera")
