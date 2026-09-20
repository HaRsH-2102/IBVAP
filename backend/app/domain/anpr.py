"""
IBVAP Domain — ANPR Event
==========================
Represents a license plate recognition event produced by the ANPR Engine (M9).

An ANPREvent is emitted when the temporal consensus threshold is reached for a
plate read across multiple frames of the same tracked vehicle.

Architectural Note:
    - ANPREvent is a domain event, not a spatial or behavioral event.
    - It carries the plate text, confidence, and the associated track.
    - The evidence dict may include crop metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class ANPREvent:
    """
    Represents a confirmed license plate recognition event.

    Attributes:
        event_id: Unique identifier for this ANPR event.
        camera_id: Source camera that captured the plate.
        track_id: Associated vehicle track ID from ByteTrack.
        plate_text: Recognized license plate text (cleaned/validated/consensus).
        raw_ocr_text: Raw un-normalized OCR text before consensus.
        plate_detection_confidence: Confidence from the plate detector model.
        confidence: OCR confidence score (0.0–1.0).
        timestamp: UTC timestamp of the consensus detection.
        vehicle_class: Object class of the tracked vehicle (car, truck, etc.).
        plate_bounding_box: Bounding box of the plate within the original frame (dict).
        vehicle_bounding_box: Bounding box of the vehicle within the original frame (dict).
        evidence: Additional metadata (plate crop size, consensus count, etc.).
    """
    event_id: str
    camera_id: str
    track_id: str
    plate_text: str
    raw_ocr_text: str
    plate_detection_confidence: float
    confidence: float
    timestamp: datetime
    plate_bounding_box: Dict[str, float]
    vehicle_bounding_box: Dict[str, float]
    vehicle_class: str = "unknown"
    evidence: Dict[str, Any] = field(default_factory=dict)
