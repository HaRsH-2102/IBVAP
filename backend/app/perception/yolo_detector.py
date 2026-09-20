"""
IBVAP Perception — YOLO Detector
================================
Concrete implementation of BaseDetector using the Ultralytics YOLO ecosystem.
"""

import time
import uuid
import logging
from typing import List, Dict

import numpy as np

# Lazy load ultralytics so the whole app doesn't crash if it's missing
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from app.domain.frame import Frame
from app.domain.detection import Detection
from app.perception.detector import BaseDetector
from app.domain.night import SceneState
from app.config import settings


class YOLODetector(BaseDetector):
    """
    Detector implementation using Ultralytics YOLO models (e.g. YOLOv8, YOLOv11).
    """

    # Standard COCO mapping for common surveillance vehicles
    COCO_CLASS_MAP: Dict[str, int] = {
        "person": 0,
        "car": 2,
        "motorcycle": 3,
        "bus": 5,
        "truck": 7
    }

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.25,
        inference_size: int = 640,
        device: str = "auto",
        enabled_classes: List[str] = None
    ):
        if YOLO is None:
            raise ImportError("Ultralytics package is not installed. Run `pip install ultralytics`.")

        self._logger = logging.getLogger("ibvap.perception.yolo")
        self.model_path = model_path
        self.conf = confidence_threshold
        self.imgsz = inference_size
        import torch
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.enabled_classes = enabled_classes or ["person", "car", "motorcycle", "bus", "truck"]
        
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

        self._logger.info(f"Loading YOLO model: {model_path} on device: {self.device}")
        
        # Load the model exactly once
        self.model = YOLO(model_path)
        
        # Ensure model is moved to device
        if self.device != "cpu":
            self.model.to(self.device)

        self._logger.info(f"YOLO model loaded. Allowed COCO IDs: {self.allowed_class_ids}")
        
        self.warmup()

    def warmup(self) -> None:
        """
        Runs a dummy image through the model to initialize CUDA context and prevent
        first-frame latency spikes.
        """
        self._logger.info("Performing model warmup...")
        start = time.perf_counter()
        
        # Create a dummy blank frame (H, W, C)
        dummy_img = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        
        # Run inference once without tracking or verbose output
        self.model.predict(
            source=dummy_img, 
            imgsz=self.imgsz, 
            device=self.device, 
            verbose=False,
            classes=self.allowed_class_ids
        )
        
        elapsed = (time.perf_counter() - start) * 1000
        self._logger.info(f"Warmup complete in {elapsed:.2f} ms")

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
            self._logger.info(f"Scene transitioned to {scene_state.name}. Adjusting M3 detection threshold: {self.conf:.2f} -> {new_conf:.2f}")
            self.conf = new_conf

    def detect(self, frame: Frame) -> List[Detection]:
        """
        Runs the YOLO model on the given frame and returns normalized Detection objects.
        """
        if frame.data is None:
            self._logger.warning(f"Frame {frame.frame_id} has no pixel data.")
            return []

        # YOLO predict
        results = self.model.predict(
            source=frame.data,
            imgsz=self.imgsz,
            device=self.device,
            conf=self.conf,
            classes=self.allowed_class_ids,
            verbose=False  # Crucial: prevents spamming the console for every frame
        )
        
        detections: List[Detection] = []
        
        # Parse the Ultralytics Results object
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
                
            # Iterate through each bounding box detected in the frame
            for i in range(len(boxes)):
                box = boxes[i]
                
                # Extract coordinates (left, top, right, bottom)
                xyxy = box.xyxy[0].tolist() 
                
                conf = float(box.conf[0].item())
                class_id = int(box.cls[0].item())
                
                semantic_class = self.id_to_semantic.get(class_id, "unknown")
                
                # Map to IBVAP standard Detection object
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
