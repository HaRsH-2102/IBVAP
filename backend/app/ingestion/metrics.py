"""
IBVAP — Stream Metrics
========================
Tracks real-time performance of a single video stream pipeline.
Records source FPS, received FPS, processed FPS, dropped frames, and processing latency.

This module is used by the CameraPipeline to measure performance.
"""

from __future__ import annotations

import time
from collections import deque


class StreamMetrics:
    """
    Tracks performance metrics for a single video stream pipeline.
    Uses sliding windows to calculate short-term averages (e.g., current FPS).
    """

    def __init__(self, window_size: int = 30) -> None:
        """
        Args:
            window_size: Number of recent samples to keep for moving averages.
        """
        self.source_fps: float = 0.0
        self.total_received: int = 0
        self.total_processed: int = 0
        self.total_dropped: int = 0

        self._window_size = window_size
        
        # Sliding windows for timestamps to calculate FPS
        self._receive_times: deque[float] = deque(maxlen=window_size)
        self._process_times: deque[float] = deque(maxlen=window_size)
        
        # Sliding window for latency measurements (in seconds)
        self._latencies: deque[float] = deque(maxlen=window_size)
        
        # Tracking metrics
        self._tracker_latencies: deque[float] = deque(maxlen=window_size)
        self.active_tracks: int = 0
        
        self.start_time: float = time.perf_counter()

    def reset(self) -> None:
        """Reset all counters and sliding windows (useful for skipping warmup frames)."""
        self.total_received = 0
        self.total_processed = 0
        self.total_dropped = 0
        self._receive_times.clear()
        self._process_times.clear()
        self._latencies.clear()
        self._tracker_latencies.clear()
        self.active_tracks = 0
        self.start_time = time.perf_counter()

    def set_source_fps(self, fps: float) -> None:
        """Set the nominal FPS declared by the source (if available)."""
        self.source_fps = fps

    def record_received(self) -> None:
        """Record that a frame was captured from the source."""
        self.total_received += 1
        self._receive_times.append(time.perf_counter())

    def record_processed(self, capture_time: float) -> None:
        """
        Record that a frame was processed.
        
        Args:
            capture_time: The perf_counter() timestamp when the frame was originally captured.
        """
        self.total_processed += 1
        now = time.perf_counter()
        self._process_times.append(now)
        if capture_time > 0:
            self._latencies.append(now - capture_time)

    def record_tracker_latency(self, latency: float) -> None:
        """Record the latency of the tracker step (in seconds)."""
        self._tracker_latencies.append(latency)
        
    def set_active_tracks(self, count: int) -> None:
        """Set the current number of active tracks."""
        self.active_tracks = count

    def record_dropped(self) -> None:
        """Record that a frame was dropped due to buffer overflow."""
        self.total_dropped += 1

    def _calculate_fps(self, times: deque[float]) -> float:
        """Calculate FPS over the sliding window."""
        if len(times) < 2:
            return 0.0
        
        duration = times[-1] - times[0]
        if duration <= 0:
            return 0.0
            
        return (len(times) - 1) / duration

    @property
    def received_fps(self) -> float:
        """Current rate of frame capture."""
        return self._calculate_fps(self._receive_times)

    @property
    def processed_fps(self) -> float:
        """Current rate of frame processing."""
        return self._calculate_fps(self._process_times)

    @property
    def average_latency(self) -> float:
        """Average processing latency in seconds over the recent window."""
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    @property
    def max_latency(self) -> float:
        """Maximum processing latency in seconds over the recent window."""
        if not self._latencies:
            return 0.0
        return max(self._latencies)

    @property
    def average_tracker_latency(self) -> float:
        """Average tracker step latency in seconds over the recent window."""
        if not self._tracker_latencies:
            return 0.0
        return sum(self._tracker_latencies) / len(self._tracker_latencies)

    def get_summary(self) -> dict[str, float | int]:
        """Return a snapshot of current metrics."""
        return {
            "source_fps": round(self.source_fps, 2),
            "received_fps": round(self.received_fps, 2),
            "processed_fps": round(self.processed_fps, 2),
            "total_received": self.total_received,
            "total_processed": self.total_processed,
            "total_dropped": self.total_dropped,
            "avg_latency_ms": round(self.average_latency * 1000, 2),
            "max_latency_ms": round(self.max_latency * 1000, 2),
            "avg_tracker_latency_ms": round(self.average_tracker_latency * 1000, 2),
            "active_tracks": self.active_tracks,
        }
