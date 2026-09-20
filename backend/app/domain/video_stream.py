"""
IBVAP Domain — VideoStream
===========================
Represents the active streaming state of a camera.

A VideoStream is a runtime/operational object — it describes the live state of
the connection to a camera's video source. It is distinct from the Camera
configuration model.

Architectural note:
    - Each Camera may have at most one active VideoStream at a time.
    - The VideoStream is not persisted — it represents in-memory runtime state.
    - Future: StreamManager (Layer 1) creates and manages VideoStream instances.
    - Future: Stream health is monitored and surfaced via the API/WebSocket layer.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class StreamState(str, Enum):
    """Lifecycle states of a video stream connection."""

    CONNECTING = "CONNECTING"   # Attempting to establish connection
    ACTIVE = "ACTIVE"           # Receiving frames successfully
    PAUSED = "PAUSED"           # Temporarily paused (e.g., resource management)
    ERROR = "ERROR"             # Connection lost or failed
    STOPPED = "STOPPED"         # Deliberately stopped


class SourceType(str, Enum):
    """Type of video source for this stream."""

    FILE = "FILE"       # Local video file (for testing)
    WEBCAM = "WEBCAM"   # Local webcam device
    RTSP = "RTSP"       # IP camera via RTSP protocol
    OTHER = "OTHER"     # Future: HLS, WebRTC, etc.


class VideoStream(BaseModel):
    """
    Represents the live streaming state of a camera connection.

    This is a runtime state object, not a persistence entity.
    It is managed by the StreamManager (Layer 1) and reflects the current
    health and configuration of an active video connection.

    Attributes:
        stream_id: Unique identifier for this stream instance.
        camera_id: The camera this stream belongs to. Foreign key to Camera.
        state: Current lifecycle state.
        source_type: Category of the video source.
        source_url: URL or device path. Credentials must come from environment config.
        resolution_width: Horizontal resolution in pixels (0 if unknown).
        resolution_height: Vertical resolution in pixels (0 if unknown).
        fps: Measured/configured frames per second (0.0 if not yet measured).
        last_frame_at: Wall-clock time of the most recently received frame.
        error_message: Human-readable error description when state is ERROR.

    Future:
        - Reconnection counter and backoff strategy
        - Stream health metrics (drop rate, latency)
        - Stream-level GPU/resource allocation
    """

    stream_id: str = Field(..., description="Unique stream instance identifier")
    camera_id: str = Field(..., description="Parent camera identifier")
    state: StreamState = Field(default=StreamState.CONNECTING)
    source_type: SourceType = Field(default=SourceType.OTHER)
    source_url: str = Field(default="", description="Video source URL or device path")
    resolution_width: int = Field(default=0, description="Horizontal resolution in pixels")
    resolution_height: int = Field(default=0, description="Vertical resolution in pixels")
    fps: float = Field(default=0.0, description="Frames per second")
    last_frame_at: datetime | None = Field(default=None, description="Timestamp of last frame")
    error_message: str | None = Field(default=None, description="Error description if in ERROR state")
