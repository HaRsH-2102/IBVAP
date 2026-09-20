# ANPR Repository Inventory

## 1. ANPR-Indian-License-Plate-Detection
- **Purpose**: Indian License Plate Detection, Tracking, and OCR
- **Detection model**: YOLOv8
- **OCR engine**: PaddleOCR
- **Tracking model**: DeepSORT
- **Pretrained weights**: `truck.pt`, `license.pt`, `ANPR2.pt` (to be verified)
- **Input types**: Video
- **Output types**: JSON, Annotated Video
- **Dataset expected**: Videos with Indian license plates
- **Python version**: 3.8+ (implied)
- **Dependencies**: ultralytics, paddleocr, deep-sort-realtime, opencv-python, torch, torchvision
- **GPU requirements**: NVIDIA GPU with CUDA
- **CUDA requirements**: Supported by PyTorch and PaddleOCR
- **Known compatibility issues**: None identified yet.
- **Main inference entry point**: `localization_ocr_enhanced.py`
- **Training code present**: Yes (`train_anpr_model.py`)
- **Inference code present**: Yes
- **Benchmark code present**: No
- **License**: MIT
- **Status**: Complete ANPR pipeline

## 2. Auto-Num-Plate-Recognition
- **Purpose**: Indian ANPR System with Streamlit web UI and FastAPI
- **Detection model**: YOLOv11
- **OCR engine**: EasyOCR + Tesseract fallback
- **Tracking model**: None explicitly mentioned (frame by frame or batch)
- **Pretrained weights**: `best.pt`
- **Input types**: Image, Video
- **Output types**: CSV, Annotated Image/Video, JSON API
- **Dataset expected**: Images or videos
- **Python version**: 3.10+
- **Dependencies**: torch, torchvision, ultralytics, easyocr, pytesseract, opencv-python, streamlit, fastapi
- **GPU requirements**: CUDA 11.8+ recommended
- **CUDA requirements**: Supported via PyTorch/EasyOCR
- **Known compatibility issues**: Tesseract must be installed on the system OS.
- **Main inference entry point**: `ocr_engine.py`, `scripts/benchmark_anpr.py`
- **Training code present**: No (just Colab notebook)
- **Inference code present**: Yes
- **Benchmark code present**: Yes (`scripts/benchmark_anpr.py`)
- **License**: MIT
- **Status**: Complete ANPR pipeline

## 3. PaddleOCR
- **Purpose**: Official PaddleOCR toolkit (likely cloned for training or as a submodule)
- **Status**: Dataset/tooling only (for our purposes, as the actual ANPR pipelines are in the above two repositories).
