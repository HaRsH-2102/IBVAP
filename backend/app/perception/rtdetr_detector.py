"""
IBVAP Perception — RT-DETR Detector
===================================
Concrete implementation of BaseDetector using the RT-DETR Transformer model.
"""

import time
import uuid
import logging
from typing import List, Dict

import numpy as np
import torch

try:
    from ultralytics import RTDETR
except ImportError:
    RTDETR = None

from app.domain.frame import Frame
from app.domain.detection import Detection
from app.perception.detector import BaseDetector
from app.domain.night import SceneState
from app.config import settings


class RTDETRDetector(BaseDetector):
    """
    Detector implementation using Ultralytics RT-DETR models.
    """

    # Standard COCO mapping for common surveillance vehicles
    COCO_CLASS_MAP: Dict[str, int] = {
        "person": 0,
        "bicycle": 1,
        "car": 2,
        "motorcycle": 3,
        "bus": 5,
        "truck": 7,
    }

    def __init__(
        self,
        model_path: str = "rtdetr-l.pt",
        confidence_threshold: float = 0.25,
        inference_size: int = 640,
        device: str = "cuda",
        use_half: bool = True,
        enabled_classes: List[str] = None
    ):
        if RTDETR is None:
            raise ImportError("Ultralytics package is not installed. Run `pip install ultralytics`.")

        self._logger = logging.getLogger("ibvap.perception.rtdetr")
        self.model_path = model_path
        self.conf = confidence_threshold
        self.imgsz = inference_size
        self.device = device if torch.cuda.is_available() else "cpu"
        self.use_half = use_half and self.device == "cuda"
            
        self.enabled_classes = enabled_classes or ["person", "car", "motorcycle", "bus", "truck", "bicycle"]
        
        # Resolve requested semantic classes to COCO IDs
        self.allowed_class_ids = []
        self.id_to_semantic = {}
        for cls_name in self.enabled_classes:
            cls_name_lower = cls_name.lower()
            if cls_name_lower in self.COCO_CLASS_MAP:
                coco_id = self.COCO_CLASS_MAP[cls_name_lower]
                self.allowed_class_ids.append(coco_id)
                self.id_to_semantic[coco_id] = cls_name_lower
            else:
                self._logger.warning(f"Class '{cls_name}' is not in standard COCO mapping and will be ignored.")

        self._logger.info(f"Loading RT-DETR model: {model_path} on device: {self.device} (FP16: {self.use_half})")
        
        # Load the model
        self.model = RTDETR(model_path)
        
        if self.device != "cpu":
            self.model.to(self.device)

        self._logger.info(f"RT-DETR model loaded. Allowed COCO IDs: {self.allowed_class_ids}")
        
    def warmup(self) -> None:
        """
        RT-DETR via Ultralytics performs warmup automatically inside predict(), 
        so manual warmup is skipped to prevent Float/Half tensor mismatch issues.
        """
        self._logger.info("Skipping explicit warmup (handled natively by Ultralytics).")
        pass

    def set_scene_state(self, scene_state: SceneState) -> None:
        """Adjust confidence threshold based on scene lighting."""
        if scene_state == SceneState.DAY:
            new_conf = settings.detector_confidence_threshold
        elif scene_state == SceneState.LOW_LIGHT:
            new_conf = settings.detector_confidence_low_light
        elif scene_state == SceneState.NIGHT:
            new_conf = settings.detector_confidence_night
        else:
            new_conf = settings.detector_confidence_threshold
            
        if self.conf != new_conf:
            self._logger.info(f"Scene transitioned to {scene_state.name}. Adjusting detection threshold: {self.conf:.2f} -> {new_conf:.2f}")
            self.conf = new_conf

    def detect(self, frame: Frame) -> List[Detection]:
        """
        Runs the RT-DETR model on the given frame and returns normalized Detection objects.
        """
        if frame.data is None:
            self._logger.warning(f"Frame {frame.frame_id} has no pixel data.")
            return []

        # Predict
        results = self.model.predict(
            source=frame.data,
            imgsz=self.imgsz,
            device=self.device,
            conf=self.conf,
            classes=self.allowed_class_ids,
            half=self.use_half,
            verbose=False
        )
        
        detections: List[Detection] = []
        
        # Parse Results
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
                
            for i in range(len(boxes)):
                box = boxes[i]
                
                xyxy = box.xyxy[0].tolist() 
                conf = float(box.conf[0].item())
                class_id = int(box.cls[0].item())
                
                semantic_class = self.id_to_semantic.get(class_id, "unknown")
                
                det = Detection(
                    detection_id=str(uuid.uuid4()),
                    camera_id=frame.camera_id,
                    frame_id=frame.frame_id,
                    timestamp=frame.timestamp,
                    class_name=semantic_class,
                    confidence=conf,
                    bbox_xyxy=(xyxy[0], xyxy[1], xyxy[2], xyxy[3])
                )
                
                detections.append(det)

        return detections
