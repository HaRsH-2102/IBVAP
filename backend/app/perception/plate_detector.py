"""
IBVAP Perception — Plate Detector
=================================
Secondary detector for finding license plates within vehicle crops.
Utilizes the FCOS (Fully Convolutional One-Stage) model from the Indian_LPR audit.
"""

import os
import sys
import time
import logging
from typing import List, Tuple

import cv2
import numpy as np
import torch

from app.config import settings

# --- Dynamically inject Indian_LPR into path ---
INDIAN_LPR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Indian_LPR-main"))
if INDIAN_LPR_DIR not in sys.path:
    sys.path.insert(0, INDIAN_LPR_DIR)

try:
    from src.object_detection.model.fcos import FCOSDetector
    from src.object_detection.model.config import DefaultConfig
    from src.object_detection.utils.utils import preprocess_image
except ImportError as e:
    logging.getLogger("ibvap.perception.plate_detector").error(f"Failed to import Indian_LPR FCOS: {e}")
    FCOSDetector = None
    DefaultConfig = None
    preprocess_image = None


class PlateDetector:
    """
    Detector implementation specifically for license plates using the FCOS model.
    Operates on vehicle crops rather than full frames.
    """

    def __init__(
        self,
        model_path: str = None,
        confidence_threshold: float = None,
        device: str = "auto"
    ):
        self._logger = logging.getLogger("ibvap.perception.plate_detector")
        
        if FCOSDetector is None:
            raise ImportError("Indian_LPR source not found or failed to load.")

        # Default to the known verified checkpoint
        self.model_path = model_path or os.path.join(INDIAN_LPR_DIR, "weights", "best_od.pth")
        self.conf = confidence_threshold or getattr(settings, "anpr_detector_confidence", 0.50)
        
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self._logger.info(f"Loading Plate FCOS model: {self.model_path} on device: {self.device}")
        
        self.model = FCOSDetector(mode="inference", config=DefaultConfig).eval()
        
        if not os.path.exists(self.model_path):
             self._logger.warning(f"Plate model weights not found at {self.model_path}")
        else:
            self.model.load_state_dict(
                torch.load(self.model_path, map_location=torch.device("cpu"))
            )
            
        if self.device != "cpu":
            self.model = self.model.cuda()

        self.warmup()

    def warmup(self) -> None:
        """Runs a dummy image through the model to initialize CUDA context."""
        self._logger.info("Performing Plate model warmup...")
        start = time.perf_counter()
        
        dummy_img = np.zeros((320, 320, 3), dtype=np.uint8)
        self.detect_in_crop(dummy_img)
        
        elapsed = (time.perf_counter() - start) * 1000
        self._logger.info(f"Plate warmup complete in {elapsed:.2f} ms")

    def detect_in_crop(self, vehicle_crop: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """
        Detects license plates within a vehicle crop image.
        Returns a list of (x1, y1, x2, y2, confidence) relative to the crop.
        """
        if vehicle_crop is None or vehicle_crop.size == 0:
            return []

        # Preprocess using Indian_LPR's utility
        image_tensor = preprocess_image(vehicle_crop.copy())
        if self.device != "cpu":
            image_tensor = image_tensor.cuda()

        with torch.no_grad():
            out = self.model(image_tensor)
            scores, classes, boxes = out
            
            # Extract results
            boxes_np = boxes[0].cpu().numpy()
            scores_np = scores[0].cpu().numpy()
            
        plates = []
        for i in range(len(boxes_np)):
            score = float(scores_np[i])
            if score >= self.conf:
                x1, y1, x2, y2 = boxes_np[i]
                
                # Enforce minimum width
                width = x2 - x1
                if width >= getattr(settings, "anpr_min_plate_width", 40):
                    plates.append((float(x1), float(y1), float(x2), float(y2), score))
                
        return plates
