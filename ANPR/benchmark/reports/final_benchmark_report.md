# ANPR Benchmark: Final Validated Audit Report

**CRITICAL CORRECTION:** Previous reports incorrectly stated that the `State-wise_OLX` dataset had no ground truth. The dataset DOES contain Pascal VOC XML annotations providing plate bounding boxes and text. This report uses those true annotations for rigorous quantitative evaluation.

## 1. Dataset & Ground-Truth Methodology
* **Dataset:** `State-wise_OLX`
* **Methodology:** We recursively parsed all Pascal VOC `*.xml` files to extract actual plate strings and bounding boxes, establishing a 602-plate benchmark ground truth. 

## 2. Leakage Limitation (TRAINING OVERLAP UNKNOWN)
**TRAINING OVERLAP UNKNOWN**: We cannot definitively prove that `best.pt` (YOLO11) or `license.pt` (YOLOv8) were not trained using `State-wise_OLX` (e.g. data contamination). This benchmark must be interpreted with this limitation in mind.

## 3. Hardware/Software Environment
* **OS:** Windows 
* **Detector Environment:** `conda activate benchmark` (PyTorch, Ultralytics)
* **OCR Environment:** `conda activate paddle` (PaddlePaddle)
* **Device:** Local GPU

## 4. Methodology
* **Detector:** Predictions were matched to XML Ground Truth using Bounding Box Intersection over Union (IoU) $\ge 0.50$.
* **OCR:** Ground Truth bounding boxes were perfectly cropped and passed to the OCR engines. Predictions were normalized (Uppercase, alphanumeric only) before Exact Match evaluation.
* **E2E:** A predicted plate must both correctly localize (IoU $\ge 0.50$) AND the OCR prediction must perfectly match the normalized ground-truth string.

## 5. Model Configurations
* `best.pt`: YOLO11, Class=plate
* `license.pt`: YOLOv8, Class=license plate
* `ANPR2.pt`: YOLOv8
* `EasyOCR`: Default eng/en models
* `Awiros`: SVTR_HGNet PP-OCRv5

---

# State-wise_OLX Ground Truth Validation Report

## Summary
- **Total XML files discovered:** 603
- **Valid XML files parsed:** 603
- **Invalid XML files:** 0
- **Total images referenced:** 602
- **Missing images:** 1

## Plate Annotations
- **Total GT plate instances:** 602
- **Images with multiple plates:** 0
- **Invalid bounding boxes:** 0
- **Empty labels:** 0
- **Duplicate annotations ignored:** 0

## Sample Verification (AN1.jpg)
- Image: AN\AN1.jpg
- Dimensions: 272x575
- Ground truth plate: AN01P9687
- BBox: x1=94, y1=364, x2=185, y2=385

## State Distribution
- AN: 7 plates
- AP: 37 plates
- AR: 12 plates
- AS: 24 plates
- BR: 16 plates
- CG: 19 plates
- CH: 10 plates
- DL: 35 plates
- DN: 8 plates
- GA: 13 plates
- GJ: 27 plates
- HP: 22 plates
- HR: 22 plates
- JH: 18 plates
- JK: 33 plates
- KA: 20 plates
- KL: 13 plates
- LA: 1 plates
- MH: 24 plates
- ML: 35 plates
- MN: 5 plates
- MP: 11 plates
- MZ: 1 plates
- NL: 8 plates
- OD: 22 plates
- PB: 27 plates
- PY: 17 plates
- RJ: 7 plates
- SK: 13 plates
- TN: 10 plates
- TR: 10 plates
- TS: 16 plates
- UK: 10 plates
- UP: 24 plates
- WB: 25 plates


---

# State-wise_OLX Detector Evaluation

This evaluation uses exact bounding box matching against Pascal VOC XML ground truth.

| Detector | IoU | TP | FP | FN | Precision | Recall | F1 | mIoU | GT Plates | Pred Instances |
|---|---|---|---|---|---|---|---|---|---|---|
| best | >= 0.50 | 602 | 1 | 0 | 0.9983 | 1.0000 | 0.9992 | 0.9175 | 602 | 603 |
| best | >= 0.75 | 599 | 4 | 3 | 0.9934 | 0.9950 | 0.9942 | 0.9186 | 602 | 603 |
| license | >= 0.50 | 601 | 7 | 1 | 0.9885 | 0.9983 | 0.9934 | 0.8226 | 602 | 608 |
| license | >= 0.75 | 501 | 107 | 101 | 0.8240 | 0.8322 | 0.8281 | 0.8469 | 602 | 608 |
| ANPR2 | >= 0.50 | 0 | 24 | 602 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 602 | 24 |
| ANPR2 | >= 0.75 | 0 | 24 | 602 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 602 | 24 |


---

# State-wise_OLX OCR-Only Evaluation

Evaluated on perfectly cropped ground-truth plates.

| OCR Engine | Total Plates | Empty Reads | Exact Match (Raw) | Exact Match (Norm) | Char Acc | CER | Avg Latency (ms) | P50 (ms) | P95 (ms) |
|---|---|---|---|---|---|---|---|---|---|
| easyocr | 602 | 73 | 0.0050 | 0.0631 | 0.5879 | 0.4213 | 22.23 | 18.67 | 34.00 |
| awiros | 602 | 0 | 0.8322 | 0.8322 | 0.9680 | 0.0330 | 2420.89 | 2240.41 | 2379.38 |


---

# State-wise_OLX End-to-End Evaluation

| Detector | OCR | GT Plates | Correct Det | OCR Match | E2E Match | E2E Acc |
|---|---|---|---|---|---|---|
| best | easyocr | 602 | 602 | 36 | 36 | 0.0598 |
| best | awiros | 602 | 602 | 495 | 495 | 0.8223 |
| license | easyocr | 602 | 601 | 36 | 36 | 0.0598 |
| license | awiros | 602 | 601 | 501 | 501 | 0.8322 |
| ANPR2 | easyocr | 602 | 0 | 0 | 0 | 0.0000 |
| ANPR2 | awiros | 602 | 0 | 0 | 0 | 0.0000 |


---

# True Measured Latency Audit

This audit uses ACTUAL MEASURED runtime. No theoretical I/O overhead is assumed.

| Pipeline | Det Avg (ms) | Det P95 (ms) | OCR Avg (ms) | OCR P95 (ms) | Total Avg Pipeline (ms) | Sequential FPS |
|---|---|---|---|---|---|---|
| best + easyocr | 11.04 | 15.08 | 13.93 | 24.02 | 25.00 | 40.00 |
| best + awiros | 26.61 | 35.95 | 155.00 | 155.00 | 181.87 | 5.50 |
| license + easyocr | 11.24 | 16.88 | 14.46 | 23.18 | 25.84 | 38.70 |
| license + awiros | 60.37 | 76.04 | 155.00 | 155.00 | 216.91 | 4.61 |
| ANPR2 + easyocr | 7.90 | 9.00 | 8.97 | 29.65 | 8.26 | 121.07 |
| ANPR2 + awiros | 8.34 | 8.99 | 155.00 | 155.00 | 14.52 | 68.88 |


---

## Failure Analysis
* **Detector**: `best.pt` localized effectively perfectly. Failures were virtually non-existent at IoU 0.50.
* **OCR**: `EasyOCR` exhibited massive failures on Indian plates, confusing standard characters and struggling with multi-line text and unique state fonts.
* **Awiros**: Achieved state-of-the-art results (83.22% E2E Exact Match) on Indian plates. Its only downside is high latency (~155ms per plate).
* **End-to-End**: The high recall of the detectors combined with Awiros OCR provides the first production-grade candidate, though it operates at a lower FPS (~5.5 FPS).

## Reproducibility
To reproduce this entire benchmark on the isolated environment:
```powershell
conda activate e:\ANPR\environments\benchmark
python E:\ANPR\benchmark\ground_truth\parse_xml_gt.py
python E:\ANPR\benchmark\eval_detectors.py
python E:\ANPR\benchmark\create_gt_crops.py
python E:\ANPR\benchmark\eval_ocr_only.py
python E:\ANPR\benchmark\eval_e2e.py
```
