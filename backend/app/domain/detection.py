"""
IBVAP Domain — Detection
========================
Represents a single detected object in a specific frame.

A Detection is the atomic unit of the perception layer. It identifies that an
object of a specific class was observed at a specific bounding box with a given
confidence.

Architectural Note:
    - Detections are stateless observations in a single frame.
    - A Detection does NOT have a track ID. Tracking is the responsibility of M4.
    - A Detection does NOT imply an event. Events are the responsibility of M5/M6.
"""

from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class ObjectClass(str, Enum):
    PERSON = "person"
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    TRUCK = "truck"

class BoundingBox(BaseModel):
    left: float
    top: float
    right: float
    bottom: float

class Detection(BaseModel):
    """
    Represents an object detected by the AI Perception layer.
    """
    detection_id: str = Field(..., description="Unique UUID for this detection")
    camera_id: str = Field(..., description="Source camera ID (propagated from Frame)")
    frame_id: str = Field(..., description="Source frame ID (propagated from Frame)")
    timestamp: datetime = Field(..., description="Wall-clock UTC time (propagated from Frame)")
    
    class_name: str = Field(..., description="Internal semantic class name (e.g., 'person', 'car')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    
    # Bounding box coordinates in pixels: (left, top, right, bottom)
    # The origin (0,0) is the top-left of the frame.
    bbox_xyxy: tuple[float, float, float, float] = Field(
        ..., 
        description="Bounding box in pixel coordinates (left, top, right, bottom)"
    )
