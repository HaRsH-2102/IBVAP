"""
IBVAP Domain — Frame
=====================
Represents one processed video frame as it moves through the pipeline.

A Frame is the fundamental unit of processing in IBVAP. Every detection,
tracking update, and spatial evaluation is anchored to a Frame.

Architectural note:
    - Frames are short-lived in memory — they are processed and the raw pixel
      data is discarded unless captured as evidence.
    - frame_id + camera_id uniquely identifies any frame in the system.
    - All downstream processing (detection, tracking, events) references
      frame_id for lineage.

Future (Milestone 2+):
    - Frame.data will carry the actual decoded pixel bytes (numpy array or raw bytes).
    - Preprocessing hooks (resize, normalize, enhance) will operate on Frame.
    - Frame objects will flow through async queues between pipeline stages.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Frame(BaseModel):
    """
    Represents one decoded video frame moving through the IBVAP pipeline.

    This is a short-lived runtime object. It carries metadata about the frame
    and optionally the raw pixel data (only when needed, e.g., for evidence capture).

    Attributes:
        frame_id: Universally unique identifier for this frame.
        camera_id: Source camera. Every frame is traceable to its camera.
        timestamp: Wall-clock UTC time when this frame was captured/decoded.
        frame_index: Sequential 0-based index within the current stream session.
            Resets when a stream reconnects.
        width: Frame width in pixels.
        height: Frame height in pixels.
        source_info: Human-readable description of the source
            (e.g., "rtsp://camera-01" or "test_video.mp4").
        data: Raw pixel data. None during normal processing to save memory.
            Populated only when evidence capture requires it.

    Future:
        - Frame preprocessing pipeline (resize, denoise, enhance for night-time)
        - Frame drop detection (gap in frame_index)
        - GPU-resident frame representation (CUDA tensor)
    """

    frame_id: str = Field(..., description="Unique frame identifier (UUID)")
    camera_id: str = Field(..., description="Source camera identifier")
    timestamp: datetime = Field(..., description="UTC time of frame capture")
    frame_index: int = Field(default=0, description="Sequential index within current stream session")
    width: int = Field(default=0, description="Frame width in pixels")
    height: int = Field(default=0, description="Frame height in pixels")
    source_info: str = Field(default="", description="Human-readable source description")
    data: Any | None = Field(
        default=None,
        description="Raw pixel data (populated only for evidence capture; None during normal processing)",
        exclude=True,  # Never serialize raw pixel data in API responses
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
