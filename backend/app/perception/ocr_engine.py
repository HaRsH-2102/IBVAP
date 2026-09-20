"""
IBVAP Perception — OCR Engine
=============================
Wraps EasyOCR for extracting text from cropped license plate images.
"""

import logging
from typing import Optional, Tuple
import numpy as np

try:
    import easyocr
except ImportError:
    easyocr = None

class OCREngine:
    def __init__(self, languages: list[str] = None, gpu: bool = True):
        if languages is None:
            languages = ['en']
            
        self._logger = logging.getLogger("ibvap.perception.ocr")
        if easyocr is None:
            self._logger.warning("EasyOCR is not installed. OCR will be disabled.")
            self.reader = None
        else:
            self._logger.info(f"Initializing EasyOCR for languages {languages} (GPU={gpu})")
            # In a production offline deployment, point model_storage_directory to a local bundled folder.
            self.reader = easyocr.Reader(languages, gpu=gpu, verbose=False)

    def read_plate(self, crop: np.ndarray) -> Optional[Tuple[str, float]]:
        """
        Reads text from a cropped numpy image array.
        Returns (text, confidence) or None if nothing found.
        """
        if self.reader is None or crop is None or crop.size == 0:
            return None
            
        # Read text, allowing only uppercase alphanumeric characters typical for plates.
        # This helps reduce false positives like reading a logo as a lowercase letter.
        results = self.reader.readtext(crop, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        
        if not results:
            return None
            
        full_text = ""
        total_conf = 0.0
        
        for (bbox, text, conf) in results:
            full_text += text
            total_conf += conf
            
        avg_conf = total_conf / len(results)
        
        # Normalize text
        normalized_text = full_text.replace(" ", "").upper()
        
        return (normalized_text, avg_conf)

    def evaluate_plausibility(self, text: str) -> float:
        """
        Evaluates the plausibility of the OCR text based on Indian standard formats.
        Returns a plausibility score [0.0, 1.0].
        Regex: ^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$ (Roughly)
        """
        import re
        
        if len(text) < 6 or len(text) > 12:
            return 0.1
            
        score = 0.5 # Base score for having reasonable length
        
        # Starts with 2 letters
        if re.match(r"^[A-Z]{2}", text):
            score += 0.2
            
        # Ends with 4 numbers
        if re.search(r"[0-9]{4}$", text):
            score += 0.2
            
        # Standard strict Indian plate regex (e.g. MH12AB1234)
        if re.match(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$", text):
            score = 1.0
            
        return score
