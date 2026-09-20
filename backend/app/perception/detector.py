"""
IBVAP Perception — Detector Interface
=====================================
Abstract base class for object detection implementations.

Following the principle of dependency inversion, the IBVAP pipeline depends on
this interface rather than a specific YOLO implementation. This guarantees that
we can swap YOLOv8 for TensorRT, ONNX, or DeepStream in the future without
altering the core application logic.
"""

from abc import ABC, abstractmethod
from typing import List

from app.domain.frame import Frame
from app.domain.detection import Detection
from app.domain.night import SceneState


class BaseDetector(ABC):
    """
    Abstract interface for object detection models.
    """

    @abstractmethod
    def detect(self, frame: Frame) -> List[Detection]:
        """
        Run inference on a single frame and return a list of detections.

        Args:
            frame (Frame): The IBVAP domain frame containing metadata and raw pixel data.

        Returns:
            List[Detection]: A list of detection objects representing found objects.
        """
        pass

    @abstractmethod
    def warmup(self) -> None:
        """
        Perform any necessary model initialization or warmup inferences.
        This ensures that the first real frame doesn't suffer an initialization latency spike.
        """
        pass

    def set_scene_state(self, scene_state: SceneState) -> None:
        """
        Dynamically adjust detection parameters based on scene lighting.
        Override in subclasses if needed.
        """
        pass
