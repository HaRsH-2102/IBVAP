# ANPR Dataset Inventory

## 1. google_images
- **Number of images**: ~442 (.jpeg, .jpg, .png)
- **Annotations available**: Yes, ~440 XML files (Pascal VOC format)
- **Ground Truth**: Plate bounding boxes and Plate Text (inside `<name>` tag).
- **Supported evaluations**: Plate detection evaluation, OCR evaluation, End-to-end ANPR evaluation.
- **Status**: Validated (Image dataset)

## 2. State-wise_OLX
- **Number of images**: ~614 (.jpg, .png)
- **Annotations available**: Yes, ~603 XML files (Pascal VOC format)
- **Ground Truth**: Plate bounding boxes and Plate Text (inside `<name>` tag).
- **Supported evaluations**: Plate detection evaluation, OCR evaluation, End-to-end ANPR evaluation.
- **Status**: Validated (Image dataset)

## 3. video_images
- **Number of images**: 642 (.jpg, .png)
- **Annotations available**: Yes, 654 XML files (Pascal VOC format)
- **Ground Truth**: Plate bounding boxes and Plate Text (inside `<name>` tag).
- **Supported evaluations**: Plate detection evaluation, OCR evaluation, End-to-end ANPR evaluation.
- **Status**: Validated (Image dataset - frames from video)

## 4. Indian-Licence-Plate-Image-Dataset-main
- **Number of images**: 34 (.jpg)
- **Annotations available**: No
- **Ground Truth**: NO_GROUND_TRUTH
- **Supported evaluations**: Only qualitative metrics (detection count, read rate, latency). Cannot calculate accuracy.
- **Status**: Validated (Image dataset, lacks GT)

## 5. Indian_LPR (https://github.com/sanchit2843/Indian_LPR)
- **Status**: UNAVAILABLE. The repository README explicitly states the dataset is not public due to legalities regarding Indian Road data. We will not use it.

## Videos
- **Number of videos**: 0 found in the workspace (`e:\ANPR`).
- **Status**: Temporal evaluation / video benchmarking will be skipped unless videos are provided.

## Ground Truth Notes
- 3 out of 4 datasets have high-quality ground truth in Pascal VOC XML format, utilizing the `<name>` tag to store the plate's alphanumeric text and `<bndbox>` for detection bounding boxes.
- For `Indian-Licence-Plate-Image-Dataset-main`, a `ground_truth_template.csv` will be provided for optional manual annotation.
- A Data Leakage Check must be performed to ensure none of our models were explicitly trained on `google_images` or `State-wise_OLX` to prevent contamination.
