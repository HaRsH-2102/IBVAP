# IBVAP Models

This directory (or the paths specified below) is intended for the large AI model weight files used by the Intelligent Border Video Analytics Platform (IBVAP).

To keep the Git repository size manageable and avoid pushing massive binary blobs, model weights (`.pt`, `.safetensors`, `.onnx`, etc.) are explicitly excluded via `.gitignore`. 

## Required Models

Please download the following models and place them in their respective expected directories before running the backend or ANPR pipeline.

### 1. RT-DETR-L (Object Detection & Spatial Intelligence)
- **Model Name:** RT-DETR Large (`rtdetr-l.pt`)
- **Purpose:** High-accuracy, real-time object detection and spatial intrusion analysis.
- **Expected Location:** `backend/rtdetr-l.pt` (or the project root depending on your `IBVAP_DETECTOR_MODEL_PATH` setting).
- **GPU Required:** Highly recommended (CUDA/FP16).

### 2. YOLOv8m (Fallback Object Detection)
- **Model Name:** YOLOv8 Medium (`yolov8m.pt`)
- **Purpose:** General-purpose or fallback object detection if RT-DETR is unavailable.
- **Expected Location:** `backend/yolov8m.pt`
- **GPU Required:** Recommended.

### 3. Awiros/PaddleOCR ANPR Text Extraction
- **Model Name:** `model.safetensors`
- **Purpose:** OCR parsing for the Automatic Number Plate Recognition (ANPR) pipeline.
- **Expected Location:** `ANPR/models/Awiros-ANPR-OCR/model.safetensors`
- **GPU Required:** Highly recommended.

## Usage Note
When running the IBVAP backend, ensure that your `.env` configuration (e.g. `IBVAP_DETECTOR_MODEL_PATH`) points to the absolute or relative path where you have placed these `.pt` files.
