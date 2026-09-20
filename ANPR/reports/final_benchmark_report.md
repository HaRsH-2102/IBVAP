# ANPR Benchmark: Final Validation Audit Report

## A. Dataset Validity
A comprehensive scan of the local workspace datasets (`State-wise_OLX`, `video_images`, `google_images`, `Indian-Licence-Plate-Image-Dataset-main`) revealed that **no usable ground-truth annotation files (XML, JSON, CSV) exist** in the tested roots. Because of this limitation, absolute precision, recall, and OCR character accuracy metrics cannot be programmatically calculated across the entire dataset out-of-the-box.

## B. Model Inventory
We audited the specific models and their architectures:
1. **`best.pt`**: Found in `Auto-Num-Plate-Recognition`. Architecture is verified as **YOLOv11** (`YOLO11`). Detects class 0 (`plate`).
2. **`license.pt`**: Found in `ANPR-Indian-License-Plate-Detection`. Architecture is verified as **YOLOv8**. Detects class 0 (`license plate`).
3. **`ANPR2.pt`**: Found in `ANPR-Indian-License-Plate-Detection`. Architecture is verified as **YOLOv8**.

## C & D & E. Detector x OCR Benchmark Results
Our pipeline sequentially processes images (Detector -> Crops -> OCR). Because automated ground-truth is missing, the "Plates Found" metric below represents the total number of bounding boxes predicted by the detector, *not* ground-truth recall.

| Dataset | Detector | OCR | Images Processed | BBoxes Predicted | Avg Det Time (ms) | Avg OCR Time (ms) | Total Latency (ms) | Sequential FPS |
|---|---|---|---|---|---|---|---|---|
| State-wise_OLX | ANPR2 | awiros | 602 | 24 | 8.34 | 158.83 | 31.06 | 32.19 |
| State-wise_OLX | ANPR2 | easyocr | 602 | 24 | 7.90 | 8.97 | 23.26 | 43.00 |
| State-wise_OLX | best | awiros | 602 | 603 | 26.61 | 155.01 | 196.88 | 5.08 |
| State-wise_OLX | best | easyocr | 602 | 603 | 11.04 | 13.93 | 39.99 | 25.00 |
| State-wise_OLX | license | awiros | 602 | 608 | 60.37 | 154.57 | 231.48 | 4.32 |
| State-wise_OLX | license | easyocr | 602 | 608 | 13.56 | 13.37 | 42.06 | 23.77 |
*(Note: Total Latency includes a 15ms base I/O overhead. FPS = 1000 / Total Latency. The missing latency for license+easyocr on State-wise_OLX has been fixed and updated.)*

## F & I. End-to-End Results & Ground-Truth Limitations
To address the missing ground truth, we randomly sampled 50 images from `State-wise_OLX` to form a **Manual Validation Set**.
The images are located in `e:\ANPR\benchmark\manual_validation\images` and a template `ground_truth.csv` has been generated.

**Action Required**:
1. Manually annotate `ground_truth.csv` with bounding boxes and text.
2. Run `python e:\ANPR\benchmark\audit_evaluate.py` to generate the final End-to-End Precision, Recall, IoU, and Character Accuracy metrics in `reports/audit_evaluate.md`.

## G. Performance Overview
From a purely computational standpoint:
* **Detection Pipeline**: `best.pt` (YOLOv11) operates at an ideal balance of speed (~11-26ms) and high activation rate (approx. 1 bounding box per image). `license.pt` (YOLOv8) is significantly slower (~60ms). `ANPR2.pt` is fast but fails to detect plates.
* **OCR Pipeline**: `easyocr` is extremely fast (~9-20ms per crop) and suitable for synchronous sequential pipelines. `awiros` (PaddleOCR HGNet) takes ~155ms per crop, capping the maximum sequential pipeline throughput at ~4-5 FPS.

## H. Failure Analysis
1. **The N/A Data Bug**: During the initial execution of `run_all.ps1`, the `State-wise_OLX + license.pt + easyocr` combination launched before the latency tracking hooks were injected into `runner.py`. The combination was isolated and re-executed, fixing the missing values.
2. **PaddleOCR/Windows Conflicts**: Standard PaddleOCR crashes PyTorch YOLO if imported in the same environment. This architectural failure was bypassed using our subprocess adapter approach.

## J. IBVAP Suitability Conclusion
**Current Hypothesis**: `best.pt` (YOLOv11) + `EasyOCR` is the strongest real-time candidate, offering ~25 FPS sequential throughput.

**Final Verdict**: This is only a throughput-based hypothesis. Because ground truth is unavailable for the bulk of the dataset, we cannot yet establish or verify the actual recognition accuracy. The ultimate decision for the production IBVAP platform must be deferred until the 50-image manual validation set is annotated and the `audit_evaluate.py` script is executed.
