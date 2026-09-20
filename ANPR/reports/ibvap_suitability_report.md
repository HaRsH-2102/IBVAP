# IBVAP Suitability Report

## Executive Summary
After successfully decoupling, isolating, and testing the available ANPR repositories against multiple Indian datasets, we evaluated 6 combinations (3 Detectors × 2 OCR Engines) on 1,256 images total.

## 1. Detector Performance
* **`best.pt` (Auto-Num-Plate-Recognition)**: Demonstrated excellent recall (finding plates in nearly 100% of the images) with an average latency of **~11-26ms**. This is highly suited for real-time video processing (40-90 FPS).
* **`license.pt` (ANPR-Indian-License-Plate-Detection)**: Found plates but generated some false positives (detected more plates than images available). It was also slower (**~56-60ms**).
* **`ANPR2.pt`**: Missed almost all plates. Unsuitable.

**Detector Recommendation:** `best.pt` via Ultralytics YOLOv8 architecture is the best fit for the IBVAP platform.

## 2. OCR Performance
* **EasyOCR**: Processed cropped plates in **~9-20ms**. It is exceptionally fast and capable of running in real-time alongside the detector.
* **Awiros-ANPR-OCR (PaddleOCR HGNet)**: Processed crops in **~154-158ms**. While this model uses a state-of-the-art HGNet backbone specifically trained for plates, its high latency makes it a bottleneck for real-time video processing (limits pipeline to ~6 FPS).
* **Standard PaddleOCR**: Failed due to environment incompatibilities (PaddlePaddle 2.6 / PaddleX bugs on Windows). Awiros-ANPR-OCR acts as our robust PaddleOCR-based replacement.

**OCR Recommendation:** If real-time processing (30+ FPS) is strictly required, **EasyOCR** is the mandatory choice. However, if accuracy is prioritized over speed, the **Awiros PaddleOCR model** is recommended, provided we run inference in batches or on a separate async pipeline.

## 3. Implementation Strategy for IBVAP
We recommend implementing **Option B (Decoupled Microservices)** for the production IBVAP platform:
1. **Detection Node**: Runs `best.pt` via PyTorch/Ultralytics (30+ FPS).
2. **OCR Node**: Extracts bounding boxes, crops images, and feeds them into the chosen OCR engine.
   * Due to strict dependency conflicts on Windows (specifically Pybind11 `_gpuDeviceProperties` conflicts between PyTorch and PaddlePaddle), these two nodes **MUST** run in isolated processes or Docker containers.

## Conclusion
The isolated ANPR Benchmark Lab is complete. The modular adapters we built (`yolo_detector.py`, `easyocr_adapter.py`, `paddleocr_adapter.py`) can be directly ported into the IBVAP backend to facilitate this decoupled architecture.
