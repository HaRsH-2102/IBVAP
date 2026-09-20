"""
IBVAP ANPR — Engine Adapters
============================

Adapter pattern to isolate ANPR engines for the benchmark.
Each engine must return a normalized output dictionary.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
import logging
import numpy as np

# A normalized output format for all benchmark engines
def create_anpr_result(
    engine: str,
    event_id: str,
    camera_id: str,
    track_id: str,
    plate_detected: bool = False,
    plate_bbox: Optional[list] = None,
    raw_text: str = "",
    normalized_text: str = "",
    plate_detection_confidence: float = 0.0,
    ocr_confidence: float = 0.0,
    processing_time_ms: float = 0.0,
    status: str = "ERROR",
    error: str = ""
) -> Dict[str, Any]:
    return {
        "engine": engine,
        "event_id": event_id,
        "camera_id": camera_id,
        "track_id": track_id,
        "plate_detected": plate_detected,
        "plate_bbox": plate_bbox,
        "raw_text": raw_text,
        "normalized_text": normalized_text,
        "plate_detection_confidence": plate_detection_confidence,
        "ocr_confidence": ocr_confidence,
        "processing_time_ms": processing_time_ms,
        "status": status,
        "error": error
    }


class BaseANPRAdapter(ABC):
    def __init__(self, name: str):
        self.name = name
        self.is_available = True
        self._logger = logging.getLogger(f"ibvap.anpr.adapters.{name}")

    @abstractmethod
    def process_crop(self, crop: np.ndarray, event_id: str, camera_id: str, track_id: str) -> Dict[str, Any]:
        """
        Takes a vehicle crop and returns a normalized ANPR result dictionary.
        Must not raise exceptions (must catch internally and return ERROR status).
        """
        pass


class FCOSAdapter(BaseANPRAdapter):
    """
    Baseline Adapter using existing IBVAP components:
    PlateDetector (FCOS best_od.pth) + OCREngine (EasyOCR)
    """
    def __init__(self):
        super().__init__("FCOS_Baseline")
        try:
            from app.perception.plate_detector import PlateDetector
            from app.perception.ocr_engine import OCREngine
            
            # Using basic configs for benchmark
            self.detector = PlateDetector()
            self.ocr = OCREngine()
        except Exception as e:
            self._logger.warning(f"Failed to load FCOS Baseline components: {e}")
            self.is_available = False

    def process_crop(self, crop: np.ndarray, event_id: str, camera_id: str, track_id: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        
        if not self.is_available:
            return create_anpr_result(
                self.name, event_id, camera_id, track_id,
                status="UNAVAILABLE", error="Engine components failed to initialize."
            )

        try:
            # 1. Plate Detection
            plate_results = self.detector.detect_in_crop(crop)
            
            if not plate_results:
                dt = (time.perf_counter() - t0) * 1000
                return create_anpr_result(
                    self.name, event_id, camera_id, track_id,
                    plate_detected=False,
                    processing_time_ms=dt,
                    status="NO_PLATE"
                )

            # Extract Plate Crop (take the highest confidence if multiple)
            best_plate = max(plate_results, key=lambda p: p[4])
            x1, y1, x2, y2, plate_conf = best_plate
            H, W, _ = crop.shape
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(W, int(x2)), min(H, int(y2))
            
            plate_crop = crop[y1:y2, x1:x2]
            
            # 2. OCR
            ocr_result = self.ocr.read_plate(plate_crop)
            
            dt = (time.perf_counter() - t0) * 1000
            
            if not ocr_result:
                return create_anpr_result(
                    self.name, event_id, camera_id, track_id,
                    plate_detected=True,
                    plate_bbox=[x1, y1, x2, y2],
                    plate_detection_confidence=plate_conf,
                    processing_time_ms=dt,
                    status="OCR_FAILED"
                )

            norm_text, ocr_conf = ocr_result
            # FCOS baseline doesn't easily return raw text via current read_plate wrapper,
            # but we simulate keeping it same for now.
            raw_text = norm_text 
            
            return create_anpr_result(
                self.name, event_id, camera_id, track_id,
                plate_detected=True,
                plate_bbox=[x1, y1, x2, y2],
                raw_text=raw_text,
                normalized_text=norm_text,
                plate_detection_confidence=plate_conf,
                ocr_confidence=ocr_conf,
                processing_time_ms=dt,
                status="SUCCESS"
            )
            
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            self._logger.error(f"FCOS Adapter failed on event {event_id}: {e}")
            return create_anpr_result(
                self.name, event_id, camera_id, track_id,
                processing_time_ms=dt,
                status="ERROR",
                error=str(e)
            )


class EasyOCRAdapter(BaseANPRAdapter):
    """
    Adapter demonstrating an alternative direct approach (using EasyOCR for detection AND reading)
    """
    def __init__(self):
        super().__init__("EasyOCR_Native")
        try:
            import easyocr
            self.reader = easyocr.Reader(['en'], gpu=True, verbose=False)
        except Exception as e:
            self._logger.warning(f"EasyOCR Native failed to initialize: {e}")
            self.is_available = False

    def process_crop(self, crop: np.ndarray, event_id: str, camera_id: str, track_id: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        if not self.is_available:
            return create_anpr_result(
                self.name, event_id, camera_id, track_id,
                status="UNAVAILABLE", error="easyocr not installed."
            )
            
        try:
            # Let EasyOCR do both detection and recognition on the vehicle crop directly
            results = self.reader.readtext(crop, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            dt = (time.perf_counter() - t0) * 1000
            
            if not results:
                return create_anpr_result(
                    self.name, event_id, camera_id, track_id,
                    plate_detected=False, processing_time_ms=dt, status="NO_PLATE"
                )
                
            # Take the highest confidence result assuming it's the plate
            best_res = max(results, key=lambda x: x[2])
            bbox, raw_text, conf = best_res
            norm_text = raw_text.replace(" ", "").upper()
            
            # extract bounding box
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            plate_box = [int(min(x_coords)), int(min(y_coords)), int(max(x_coords)), int(max(y_coords))]
            
            return create_anpr_result(
                self.name, event_id, camera_id, track_id,
                plate_detected=True,
                plate_bbox=plate_box,
                raw_text=raw_text,
                normalized_text=norm_text,
                plate_detection_confidence=conf, # easyocr gives combined confidence
                ocr_confidence=conf,
                processing_time_ms=dt,
                status="SUCCESS"
            )
            
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            return create_anpr_result(
                self.name, event_id, camera_id, track_id,
                processing_time_ms=dt, status="ERROR", error=str(e)
            )

class PaddleOCRAdapter(BaseANPRAdapter):
    def __init__(self):
        super().__init__("PaddleOCR")
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
        except Exception:
            self.is_available = False

    def process_crop(self, crop: np.ndarray, event_id: str, camera_id: str, track_id: str) -> Dict[str, Any]:
        if not self.is_available:
            return create_anpr_result(
                self.name, event_id, camera_id, track_id,
                status="UNAVAILABLE", error="paddleocr not installed."
            )
        # Real implementation would go here
        return create_anpr_result(self.name, event_id, camera_id, track_id, status="ERROR", error="Not fully implemented for test")
