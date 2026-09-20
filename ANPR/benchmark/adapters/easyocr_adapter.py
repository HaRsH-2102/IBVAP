from typing import List, Dict
import numpy as np
import easyocr
import torch
from .base import BaseOCR

class EasyOCRAdapter(BaseOCR):
    def __init__(self, langs: List[str] = ['en']):
        self.langs = langs
        self.load_model()

    def load_model(self, model_path: str = None):
        use_gpu = torch.cuda.is_available()
        self.reader = easyocr.Reader(self.langs, gpu=use_gpu)

    def recognize(self, image: np.ndarray) -> List[Dict]:
        results = self.reader.readtext(image)
        recognitions = []
        for (bbox, text, prob) in results:
            # bbox is a list of 4 points: [[x,y], [x,y], [x,y], [x,y]]
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)
            
            recognitions.append({
                'box': [int(x1), int(y1), int(x2), int(y2)],
                'text': text,
                'confidence': float(prob)
            })
        return recognitions
