# video_images Manual Validation Report

> [!IMPORTANT]
> No ground-truth scoring was performed. Results are intended for manual visual inspection and operational/runtime validation.

## 1. Dataset Inventory & Deduplication
- **Location:** `E:\ANPR\video_images`
- **Physical Files Discovered:** 654
- **Unique Images Processed:** 654
- **Duplicates Skipped:** 0 (from `sample_datasets/`)

## 2. Environment
- **Models:** YOLO11 (`best.pt`), YOLOv8 (`license.pt`)
- **OCR Engine:** Awiros (`PaddleOCRAdapter`)
- **Execution:** Isolated in `E:\ANPR\benchmark` (IBVAP unmodified)

## 3. Operational Statistics

### best.pt + awiros
- **Images with detections:** 653
- **Total plate detections:** 655
- **OCR Attempts:** 655
- **Non-empty reads:** 655
- **Sequential FPS:** 43.79
- **Latency (Avg):** 22.8ms

### license.pt + awiros
- **Images with detections:** 654
- **Total plate detections:** 681
- **OCR Attempts:** 681
- **Non-empty reads:** 681
- **Sequential FPS:** 42.81
- **Latency (Avg):** 23.4ms

## 4. Visual Inspection Categories
Representative visual samples are located at:
`E:\ANPR\benchmark\results\video_images_validation\20260917_162118\visual_review`

*Please review the images for:*
- Successful-looking examples
- OCR failures
- Detection failures
- False positives
- Difficult / Angled plates
- Small plates

## 5. Output Paths
- **best.pt annotated images:** `E:\ANPR\benchmark\results\video_images_validation\20260917_162118\best_awiros\annotated_images`
- **license.pt annotated images:** `E:\ANPR\benchmark\results\video_images_validation\20260917_162118\license_awiros\annotated_images`
- **Plate crops:** In respective `plate_crops/` folders
- **Mapping logs:** In respective `mapping.jsonl`

## 6. Observed Limitations / Errors
- No major execution errors occurred during processing. All identical duplicated images were safely hashed and skipped.
