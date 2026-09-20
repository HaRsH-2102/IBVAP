from typing import List, Dict
import numpy as np
import torch
from ultralytics import YOLO
from .base import BaseDetector

class YOLODetector(BaseDetector):
    def __init__(self, model_path: str):
        self.load_model(model_path)

    def load_model(self, model_path: str):
        self.model = YOLO(model_path)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    def detect(self, image: np.ndarray) -> List[Dict]:
        results = self.model(image, verbose=False, device=self.device)
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = self.model.names[int(box.cls[0])]
                detections.append({
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': conf,
                    'class': cls
                })
        return detections
