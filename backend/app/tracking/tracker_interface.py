"""
IBVAP — Tracking Interface
==========================
Defines the `BaseTracker` abstraction for all Multi-Object Trackers.

The tracker is responsible for associating frame-level `Detection` snapshots
into temporal `Track` identities.
"""

from abc import ABC, abstractmethod

from app.domain.detection import Detection
from app.domain.track import Track
from app.ingestion.frame_pipeline import Frame


class BaseTracker(ABC):
    """
    Abstract interface for Multi-Object Tracking algorithms.
    
    A Tracker consumes `Detection` objects from the Detector and outputs
    `Track` objects. It does NOT interact directly with the AI model.
    """
    
    @abstractmethod
    def update(self, detections: list[Detection], frame: Frame) -> list[Track]:
        """
        Update the tracking state with new detections from the current frame.
        
        Args:
            detections: List of objects detected in the current frame.
            frame: The current Frame object (provides timestamps and frame ID).
            
        Returns:
            A list of all currently active and lost (but not removed) tracks.
        """
        pass
