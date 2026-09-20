"""
IBVAP — Video Ingestion Layer (Layer 1)
========================================
StreamManager: Manages per-camera video stream acquisition.

This module defines the abstract boundary for video stream management.
No actual frame acquisition is implemented in Milestone 1.

Architectural note:
    - Each camera has its own StreamManager context.
    - Failures in one camera's StreamManager must not affect others.
    - Future implementations will use OpenCV/FFmpeg for frame acquisition.
    - The StreamManager is the ONLY component that knows about video source details.
      Downstream layers receive Frame objects — they never touch raw stream handles.

Future (Milestone 2):
    - FileStreamManager: Read from local video files
    - WebcamStreamManager: Capture from local webcam device
    - RTSPStreamManager: Connect to IP cameras via RTSP
    - Reconnection and backoff logic
    - Per-camera async frame queues
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.frame import Frame
from app.domain.video_stream import VideoStream
from app.logging_config import get_logger

logger = get_logger(__name__)


class BaseStreamManager(ABC):
    """
    Abstract base class for video stream acquisition.

    Each concrete implementation handles a specific source type
    (file, webcam, RTSP) and produces Frame objects for downstream processing.

    All implementations must:
    - Be isolated per camera (one instance per camera)
    - Handle their own connection/reconnection logic
    - Catch and log exceptions without propagating to other camera contexts
    - Update the associated VideoStream state on connection changes

    Implementation target (Milestone 2):
        class RTSPStreamManager(BaseStreamManager):
            def connect(self) -> VideoStream: ...
            def read_frame(self) -> Frame | None: ...
            def disconnect(self) -> None: ...
    """

    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self._logger = get_logger(f"ibvap.ingestion.{camera_id}")

    @abstractmethod
    def connect(self) -> VideoStream:
        """
        Establish connection to the video source.

        Returns:
            VideoStream: The stream object representing the active connection.

        Raises:
            StreamException: If connection cannot be established.

        Future implementation must update VideoStream.state appropriately.
        """
        raise NotImplementedError("Milestone 2: Implement in concrete StreamManager subclasses")

    @abstractmethod
    def read_frame(self) -> Frame | None:
        """
        Read the next frame from the video source.

        Returns:
            Frame: The decoded frame with metadata, or None if no frame is available.

        Raises:
            FrameException: If frame decoding fails.
            StreamException: If the connection is lost.

        This method will be called in a tight loop by the processing pipeline.
        """
        raise NotImplementedError("Milestone 2: Implement in concrete StreamManager subclasses")

    @abstractmethod
    def disconnect(self) -> None:
        """
        Gracefully disconnect from the video source.
        Should release all resources (file handles, network connections, GPU buffers).
        """
        raise NotImplementedError("Milestone 2: Implement in concrete StreamManager subclasses")

    @abstractmethod
    def get_stream_state(self) -> VideoStream:
        """Return the current VideoStream state object."""
        raise NotImplementedError("Milestone 2: Implement in concrete StreamManager subclasses")
