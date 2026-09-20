"""
IBVAP — Frame Processing Pipeline
=================================
Manages the concurrent capture and buffering of frames.
Decouples the capture process (I/O bound) from the processing logic.

Features:
- Dedicated capture thread per camera
- Bounded thread-safe frame queue
- Frame dropping policy prioritizing lowest latency
- Playback speed regulation (real-time vs max throughput)
"""

from __future__ import annotations

import time
import queue
import threading
from typing import Callable, Optional

from app.config import settings
from app.domain.frame import Frame
from app.domain.video_stream import SourceType
from app.ingestion.stream_manager import BaseStreamManager
from app.ingestion.metrics import StreamMetrics
from app.logging_config import get_logger


class CameraPipeline:
    """
    Manages the lifecycle of video acquisition for a single camera.
    Uses a dedicated thread to capture frames into a bounded queue,
    allowing downstream processors to pull frames without blocking the source.
    """

    def __init__(
        self,
        stream_manager: BaseStreamManager,
        metrics: StreamMetrics,
        buffer_capacity: int = settings.frame_buffer_capacity,
        playback_mode: str = settings.playback_mode
    ):
        self.stream_manager = stream_manager
        self.metrics = metrics
        self.buffer_capacity = buffer_capacity
        self.playback_mode = playback_mode
        self.camera_id = stream_manager.camera_id
        self._logger = get_logger(f"ibvap.pipeline.{self.camera_id}")

        # Thread-safe bounded queue for frames
        self._frame_queue: queue.Queue[tuple[Frame, float]] = queue.Queue(maxsize=buffer_capacity)
        
        self._is_running = False
        self._capture_thread: threading.Thread | None = None
        
        # State tracking for real-time simulation
        self._last_frame_ts: float | None = None
        self._last_capture_time: float | None = None
        
        self.playback_speed: float = 1.0
        self.is_paused: bool = False

    def start(self) -> None:
        """Connect to the source and start the background capture thread."""
        if self._is_running:
            return

        self._logger.info("Starting CameraPipeline")
        
        try:
            stream_state = self.stream_manager.connect()
            self.metrics.set_source_fps(stream_state.fps)
            
            self._is_running = True
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                name=f"CaptureThread-{self.camera_id}",
                daemon=True
            )
            self._capture_thread.start()
            
        except Exception as e:
            self._logger.error(f"Failed to start pipeline: {e}")
            raise

    def _capture_loop(self) -> None:
        """
        Background thread loop continuously reading frames from the stream manager.
        """
        self._logger.info("Capture thread started")
        
        try:
            while self._is_running:
                if self.is_paused:
                    time.sleep(0.1)
                    # When paused, we don't want to mess up real-time playback calc upon resume
                    self._last_capture_time = None
                    continue
                    
                # Measure capture duration
                start_read = time.perf_counter()
                
                # 1. Read Frame
                frame = self.stream_manager.read_frame()
                
                if frame is None:
                    # End of file reached
                    self._logger.info("Source provided None (EOF or graceful disconnect). Stopping capture.")
                    break
                
                capture_time = time.perf_counter()
                self.metrics.record_received()
                
                # 2. Playback speed regulation (for FILE sources in real-time mode)
                self._regulate_playback_speed(frame.timestamp.timestamp(), start_read)

                # 3. Buffer Management (Overflow Policy)
                # If queue is full, we must drop the oldest frame to maintain low latency
                while True:
                    try:
                        self._frame_queue.put_nowait((frame, capture_time))
                        break  # Successfully put the frame
                    except queue.Full:
                        # Queue is full, discard the oldest frame
                        try:
                            dropped_frame, _ = self._frame_queue.get_nowait()
                            self.metrics.record_dropped()
                        except queue.Empty:
                            # Edge case: consumer pulled it just before we reached here
                            pass
                        
        except Exception as e:
            self._logger.error(f"Capture loop encountered an error: {e}")
        finally:
            self._is_running = False
            self.stream_manager.disconnect()
            self._logger.info("Capture thread terminated")

    def _regulate_playback_speed(self, frame_timestamp: float, start_read_time: float) -> None:
        """
        Regulates processing speed to simulate real-time playback for prerecorded files.
        If playback_mode == 'max_throughput', this method does nothing.
        """
        if self.playback_mode != "real_time" or self.stream_manager.get_stream_state().source_type != SourceType.FILE:
            return

        if self._last_frame_ts is not None and self._last_capture_time is not None:
            # Difference in video timestamp (seconds)
            ts_diff = frame_timestamp - self._last_frame_ts
            
            # How much time has passed in reality since the last capture started
            elapsed_real = time.perf_counter() - self._last_capture_time
            
            # If we are processing faster than real time, sleep the difference
            sleep_time = (ts_diff / max(0.1, self.playback_speed)) - elapsed_real
            if sleep_time > 0:
                time.sleep(sleep_time)

        self._last_frame_ts = frame_timestamp
        self._last_capture_time = time.perf_counter()

    def get_next_frame(self, timeout: float | None = 1.0) -> Frame | None:
        """
        Pull the next frame from the buffer for processing.
        This is called by the downstream consumer.
        
        Args:
            timeout: How long to wait for a frame.
            
        Returns:
            The Frame if available, or None if timeout occurs or pipeline stops.
        """
        try:
            frame, capture_time = self._frame_queue.get(timeout=timeout)
            self.metrics.record_processed(capture_time)
            return frame
        except queue.Empty:
            return None

    def stop(self) -> None:
        """Gracefully stop the pipeline and release resources."""
        self._logger.info("Stopping CameraPipeline")
        self._is_running = False
        
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
            
        # Empty the queue
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break
        
        self.stream_manager.disconnect()
        self._logger.info("Pipeline stopped")

    def seek(self, timestamp_sec: float) -> None:
        """Seek to a specific time and clear the backlog queue."""
        if hasattr(self.stream_manager, 'seek'):
            # Clear queue
            while not self._frame_queue.empty():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    break
                    
            self.stream_manager.seek(timestamp_sec)
            self._last_capture_time = None
            self._last_frame_ts = None

    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def queue_size(self) -> int:
        return self._frame_queue.qsize()
