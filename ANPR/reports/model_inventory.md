# ANPR Model Inventory

## Detection Models

### 1. license.pt
- **Model name**: license.pt
- **Model type**: Plate detector (YOLOv8s based on size)
- **Framework**: Ultralytics PyTorch
- **Version**: YOLOv8
- **Weights path**: `e:\ANPR\ANPR-Indian-License-Plate-Detection\license.pt`
- **Input resolution**: ~640x640 (standard YOLO)
- **Expected input**: Image (numpy array / BGR)
- **Expected output**: Bounding boxes, confidence, class IDs
- **GPU support**: Yes (CUDA via PyTorch)
- **License**: Unknown (Custom weights)
- **Source repository**: `ANPR-Indian-License-Plate-Detection`
- **Inference API**: `ultralytics.YOLO`
- **Dependencies**: ultralytics, torch

### 2. ANPR2.pt
- **Model name**: ANPR2.pt
- **Model type**: Plate detector (YOLOv8n based on size)
- **Framework**: Ultralytics PyTorch
- **Version**: YOLOv8
- **Weights path**: `e:\ANPR\ANPR-Indian-License-Plate-Detection\ANPR2.pt`
- **Input resolution**: ~640x640
- **Expected input**: Image (numpy array / BGR)
- **Expected output**: Bounding boxes, confidence, class IDs
- **GPU support**: Yes (CUDA via PyTorch)
- **License**: Unknown
- **Source repository**: `ANPR-Indian-License-Plate-Detection`
- **Inference API**: `ultralytics.YOLO`
- **Dependencies**: ultralytics, torch

### 3. best.pt
- **Model name**: best.pt
- **Model type**: Plate detector (YOLOv11n based on size)
- **Framework**: Ultralytics PyTorch
- **Version**: YOLOv11
- **Weights path**: `e:\ANPR\Auto-Num-Plate-Recognition\best.pt`
- **Input resolution**: 640x640
- **Expected input**: Image (numpy array / BGR)
- **Expected output**: Bounding boxes, confidence, class IDs
- **GPU support**: Yes (CUDA via PyTorch)
- **License**: MIT (part of repo)
- **Source repository**: `Auto-Num-Plate-Recognition`
- **Inference API**: `ultralytics.YOLO`
- **Dependencies**: ultralytics, torch

## OCR Models / Engines

### 1. PaddleOCR
- **Model name**: PaddleOCR (en)
- **Model type**: Text Detection & Recognition
- **Framework**: PaddlePaddle
- **Version**: >=2.6
- **Weights path**: Downloaded at runtime
- **Expected input**: Cropped plate image
- **Expected output**: Recognized text, confidence
- **GPU support**: Yes (`paddlepaddle-gpu`)
- **License**: Apache 2.0
- **Source repository**: `PaddleOCR`
- **Inference API**: `paddleocr.PaddleOCR`
- **Dependencies**: paddleocr, paddlepaddle-gpu

### 2. EasyOCR
- **Model name**: EasyOCR (en)
- **Model type**: Text Detection & Recognition
- **Framework**: PyTorch
- **Version**: >=1.7
- **Weights path**: Downloaded at runtime
- **Expected input**: Cropped plate image
- **Expected output**: Recognized text, confidence
- **GPU support**: Yes
- **License**: Apache 2.0
- **Source repository**: `Auto-Num-Plate-Recognition`
- **Inference API**: `easyocr.Reader`
- **Dependencies**: easyocr, torch

### 3. Tesseract
- **Model name**: Tesseract OCR
- **Model type**: Optical Character Recognition
- **Framework**: Tesseract (C++)
- **Version**: >=4.0
- **Weights path**: System installation
- **Expected input**: Cropped preprocessed image
- **Expected output**: Recognized text string
- **GPU support**: No (CPU only)
- **License**: Apache 2.0
- **Source repository**: System package
- **Inference API**: `pytesseract.image_to_string`
- **Dependencies**: pytesseract, tesseract-ocr (OS level)

### 4. Awiros-ANPR-OCR
- **Model name**: Awiros-ANPR-OCR
- **Model type**: Text Recognition (Indian specific)
- **Architecture**: PP-OCRv5 / SVTR_HGNet / PPHGNetV2_B4
- **Framework**: PaddleOCR / SafeTensors
- **Weights path**: `e:\ANPR\models\Awiros-ANPR-OCR`
- **Size**: ~37.3M parameters
- **Expected input**: Cropped plate image (supports two-row plates)
- **Expected output**: Recognized text, confidence
- **GPU support**: Yes
- **License**: Apache 2.0
- **Source repository**: https://huggingface.co/Awiros/anpr-ocr
- **Inference API**: `paddleocr` integrated via `BaseOCREngine`
- **Dependencies**: paddleocr, huggingface_hub
