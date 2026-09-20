"""
IBVAP — OpenCV Stream Managers
================================
Implements BaseStreamManager using OpenCV VideoCapture.
Supports files, webcams, and RTSP sources (architecturally).

This is the Milestone 2 decoder layer. Future optimization (Milestone 18)
may replace or supplement this with FFmpeg or NVIDIA DeepStream.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
import cv2
import numpy as np
from typing import Any

from app.domain.frame import Frame
from app.domain.video_stream import VideoStream, StreamState, SourceType
from app.ingestion.stream_manager import BaseStreamManager
from app.exceptions import StreamException, FrameException


class OpenCVStreamManager(BaseStreamManager):
    """
    Base implementation for OpenCV-based stream managers.
    Handles the underlying cv2.VideoCapture lifecycle and Frame creation.
    """

    def __init__(self, camera_id: str, source_type: SourceType, source_path: str | int):
        super().__init__(camera_id)
        self.source_type = source_type
        self.source_path = source_path
        self._cap: cv2.VideoCapture | None = None
        self._stream_state: VideoStream = VideoStream(
            stream_id=f"stream_{camera_id}",
            camera_id=camera_id,
            state=StreamState.STOPPED,
            source_type=source_type
        )
        self._frame_counter: int = 0
        self._source_fps: float = 0.0

    def connect(self) -> VideoStream:
        """Establish connection to the video source."""
        self._logger.info(f"Connecting to source {self.source_path} ({self.source_type})")
        
        try:
            self._cap = cv2.VideoCapture(self.source_path)
            if not self._cap.isOpened():
                raise StreamException(f"Failed to open source: {self.source_path}")
            
            # Read metadata
            self._source_fps = self._cap.get(cv2.CAP_PROP_FPS)
            width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self._stream_state.state = StreamState.ACTIVE
            self._stream_state.fps = self._source_fps
            
            self._logger.info(
                f"Source opened successfully: {width}x{height} @ {self._source_fps} FPS"
            )
            return self._stream_state
            
        except Exception as e:
            self._stream_state.state = StreamState.ERROR
            self._logger.error(f"Connection failed: {e}")
            if self._cap:
                self._cap.release()
                self._cap = None
            raise StreamException(f"Connection error: {e}") from e

    def read_frame(self) -> Frame | None:
        """
        Read the next frame from the video source.
        Returns None on EOF for files, or raises an exception for live streams if dropped.
        """
        if not self._cap or not self._cap.isOpened():
            raise StreamException("Cannot read frame: source is not connected")

        ret, cv_frame = self._cap.read()
        
        if not ret:
            # For a file, this usually means EOF
            if self.source_type == SourceType.FILE:
                self._logger.info("End of file reached")
                return None
            else:
                # For live streams, a failed read implies disconnection
                self._stream_state.state = StreamState.ERROR
                raise StreamException("Stream disconnected or frame read failed")

        self._frame_counter += 1
        
        # Source timestamp based on video file position or current time for live
        if self.source_type == SourceType.FILE:
            # Try to get timestamp from video file (in milliseconds)
            ts_ms = self._cap.get(cv2.CAP_PROP_POS_MSEC)
            timestamp_sec = ts_ms / 1000.0 if ts_ms >= 0 else time.time()
        else:
            timestamp_sec = time.time()
            
        timestamp_dt = datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)

        frame = Frame(
            frame_id=f"f_{self.camera_id}_{self._frame_counter}",
            camera_id=self.camera_id,
            timestamp=timestamp_dt,
            width=cv_frame.shape[1],
            height=cv_frame.shape[0],
            data=cv_frame
        )
        return frame

    def disconnect(self) -> None:
        """Gracefully disconnect and release resources."""
        if self._cap:
            self._logger.info("Releasing VideoCapture resources")
            self._cap.release()
            self._cap = None
        self._stream_state.state = StreamState.STOPPED
        self._logger.info("Stream disconnected")

    def seek(self, timestamp_sec: float) -> bool:
        """Seek to a specific timestamp in the video file."""
        if self.source_type != SourceType.FILE or not self._cap or not self._cap.isOpened():
            return False
            
        try:
            self._cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000.0)
            self._logger.info(f"Seeked to {timestamp_sec}s")
            return True
        except Exception as e:
            self._logger.error(f"Failed to seek: {e}")
            return False

    def get_stream_state(self) -> VideoStream:
        return self._stream_state


class FileStreamManager(OpenCVStreamManager):
    """Manages video acquisition from a local file."""
    def __init__(self, camera_id: str, file_path: str):
        super().__init__(camera_id, SourceType.FILE, file_path)


class WebcamStreamManager(OpenCVStreamManager):
    """Manages live capture from a local webcam device."""
    def __init__(self, camera_id: str, device_id: int = 0):
        super().__init__(camera_id, SourceType.WEBCAM, device_id)


class RTSPStreamManager(OpenCVStreamManager):
    """
    Manages live capture from an RTSP IP camera.
    Note: RTSP configuration may require advanced cv2 environment variables
    for buffer sizing and timeouts in production (Milestone 18).
    """
    def __init__(self, camera_id: str, rtsp_url: str):
        # Set OpenCV environment variables for low-latency RTSP if needed here
        super().__init__(camera_id, SourceType.RTSP, rtsp_url)
