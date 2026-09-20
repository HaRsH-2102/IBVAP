"""
IBVAP — AI Perception Layer (Layer 3)
=======================================
BaseDetector: Abstract interface for all AI detection models.

This module defines the contract between the AI perception layer and all
downstream components. No actual AI model is implemented here.

CRITICAL architectural rule:
    No component outside this package may import PyTorch, CUDA, YOLO,
    or any model-specific library. All AI results cross this boundary
    as Detection domain objects.

    WRONG:  from ultralytics import YOLO  ← in event_engine.py
    RIGHT:  from app.perception.detector_interface import BaseDetector

Future AI integrations (Milestone 3+):
    class YOLOv8Detector(BaseDetector):
        \"\"\"YOLO-based detector using Ultralytics ecosystem.\"\"\"
        def load(self) -> None: ...
        def detect(self, frame: Frame) -> list[Detection]: ...

    class RetinaFaceDetector(BaseDetector):
        \"\"\"Face detector using RetinaFace.\"\"\"
        def load(self) -> None: ...
        def detect(self, frame: Frame) -> list[Detection]: ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.detection import Detection
from app.domain.frame import Frame
from app.logging_config import get_logger

logger = get_logger(__name__)


class BaseDetector(ABC):
    """
    Abstract base class for all AI object detection models.

    All detectors must implement this interface. The rest of the system
    only interacts with detectors through this boundary — never through
    model-specific APIs.

    Responsibilities:
        - Load model weights at startup
        - Accept a Frame and return zero or more Detection objects
        - Map model-native class names to the ObjectClass enum
        - Apply confidence thresholding before returning
        - Handle inference errors internally and raise InferenceException

    Design for replaceability:
        If ByteTrack is replaced by BoT-SORT, ONLY the BaseTracker subclass changes.
        If YOLO is replaced by another detector, ONLY the BaseDetector subclass changes.
        Event engine, risk engine, spatial engine: zero changes required.

    Attributes:
        model_name: Identifier string for this model (e.g., "yolov8n", "yolov8x").
        confidence_threshold: Minimum confidence to return a detection.
        is_loaded: Whether the model weights are currently loaded.
    """

    def __init__(self, model_name: str, confidence_threshold: float = 0.5) -> None:
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.is_loaded = False
        self._logger = get_logger(f"ibvap.perception.{model_name}")

    @abstractmethod
    def load(self) -> None:
        """
        Load model weights into memory (and optionally to GPU).

        Must set self.is_loaded = True on success.

        Raises:
            ModelLoadException: If weights cannot be found or loaded.

        Future: GPU device selection based on system configuration.
        """
        raise NotImplementedError("Milestone 3: Implement in concrete detector subclasses")

    @abstractmethod
    def detect(self, frame: Frame) -> list[Detection]:
        """
        Run inference on a single frame and return detection results.

        This method is called once per frame in the processing pipeline.
        It must be as fast as possible — it is on the critical path for real-time processing.

        Args:
            frame: The Frame to run inference on. frame.data must be populated.

        Returns:
            List of Detection objects (may be empty if nothing detected).
            Only detections above self.confidence_threshold should be returned.

        Raises:
            InferenceException: If inference fails (model error, OOM, etc.).
            RuntimeError: If called before load() has been called.
        """
        raise NotImplementedError("Milestone 3: Implement in concrete detector subclasses")

    @abstractmethod
    def unload(self) -> None:
        """
        Release model from memory (GPU and CPU).
        Called during system shutdown or when swapping models.
        """
        raise NotImplementedError("Milestone 3: Implement in concrete detector subclasses")
