from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
import numpy as np

class BaseDetector(ABC):
    @abstractmethod
    def load_model(self, model_path: str):
        pass

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[Dict]:
        """
        Returns list of dicts: {'box': [x1, y1, x2, y2], 'confidence': float, 'class': str}
        """
        pass

class BaseOCR(ABC):
    @abstractmethod
    def load_model(self, model_path: str = None):
        pass

    @abstractmethod
    def recognize(self, image: np.ndarray) -> List[Dict]:
        """
        Returns list of dicts: {'text': str, 'confidence': float, 'box': [x1, y1, x2, y2]}
        """
        pass

class BasePipeline(ABC):
    @abstractmethod
    def run(self, image: np.ndarray) -> List[Dict]:
        """
        Returns list of dicts: {'box': [x1, y1, x2, y2], 'text': str, 'text_confidence': float}
        """
        pass
