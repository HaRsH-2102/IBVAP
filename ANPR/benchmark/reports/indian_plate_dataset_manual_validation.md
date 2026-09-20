# Indian Licence Plate Dataset Manual Validation Report

> [!IMPORTANT]
> No ground-truth scoring was performed. Results are intended for manual visual inspection and operational/runtime validation.

## 1. Dataset Inventory & Deduplication
- **Location:** `E:\ANPR\Indian-Licence-Plate-Image-Dataset-main`
- **Physical Files Discovered:** 34
- **Unique Images Processed:** 17
- **Duplicates Skipped:** 17 (from `sample_datasets/`)

## 2. Environment
- **Models:** YOLO11 (`best.pt`), YOLOv8 (`license.pt`)
- **OCR Engine:** Awiros (`PaddleOCRAdapter`)
- **Execution:** Isolated in `E:\ANPR\benchmark` (IBVAP unmodified)

## 3. Operational Statistics

### best.pt + awiros
- **Images with detections:** 14
- **Total plate detections:** 14
- **OCR Attempts:** 14
- **Non-empty reads:** 14
- **Sequential FPS:** 9.73
- **Latency (Avg):** 102.8ms

### license.pt + awiros
- **Images with detections:** 16
- **Total plate detections:** 17
- **OCR Attempts:** 17
- **Non-empty reads:** 17
- **Sequential FPS:** 9.31
- **Latency (Avg):** 107.4ms

## 4. Visual Inspection Categories
Representative visual samples are located at:
`E:\ANPR\benchmark\results\indian_plate_dataset\20260917_161025\visual_review`

*Please review the images for:*
- Successful-looking examples
- OCR failures
- Detection failures
- False positives
- Difficult / Angled plates
- Small plates

## 5. Output Paths
- **best.pt annotated images:** `E:\ANPR\benchmark\results\indian_plate_dataset\20260917_161025\best_awiros\annotated_images`
- **license.pt annotated images:** `E:\ANPR\benchmark\results\indian_plate_dataset\20260917_161025\license_awiros\annotated_images`
- **Plate crops:** In respective `plate_crops/` folders
- **Mapping logs:** In respective `mapping.jsonl`

## 6. Observed Limitations / Errors
- No major execution errors occurred during processing. All identical duplicated images were safely hashed and skipped.
