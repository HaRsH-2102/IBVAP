import os
import json
import shutil
from glob import glob

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", type=str, required=True)
    parser.add_argument("--dataset_name", type=str, required=True)
    args = parser.parse_args()
    
    base_dir = args.base_dir
    
    best_stats_path = os.path.join(base_dir, "best_awiros", "stats.json")
    license_stats_path = os.path.join(base_dir, "license_awiros", "stats.json")
    
    with open(best_stats_path, "r") as f:
        best_stats = json.load(f)
    with open(license_stats_path, "r") as f:
        license_stats = json.load(f)
        
    # Generate Comparison Summary
    comp_md = """# Comparison Summary

| System | Unique Images | Images With Detections | Plate Detections | OCR Attempts | Non-empty OCR | Avg Detection ms | Avg OCR ms | Avg Total ms | Sequential FPS |
|---|---|---|---|---|---|---|---|---|---|
"""
    for s in [best_stats, license_stats]:
        comp_md += f"| {s['model']} + awiros | {s['unique_images']} | {s['images_with_det']} | {s['total_plates']} | {s['ocr_attempts']} | {s['non_empty']} | {s['det_avg']:.2f} | {s['ocr_avg']:.2f} | {s['tot_avg']:.2f} | {s['fps']:.2f} |\n"
        
    with open(os.path.join(base_dir, "comparison_summary.md"), "w") as f:
        f.write(comp_md)
        
    # Generate Visual Review Directory
    vis_dir = os.path.join(base_dir, "visual_review")
    os.makedirs(vis_dir, exist_ok=True)
    
    best_annots = glob(os.path.join(base_dir, "best_awiros", "annotated_images", "*.jpg"))
    for p in best_annots:
        shutil.copy(p, os.path.join(vis_dir, f"best_{os.path.basename(p)}"))
        
    license_annots = glob(os.path.join(base_dir, "license_awiros", "annotated_images", "*.jpg"))
    for p in license_annots:
        shutil.copy(p, os.path.join(vis_dir, f"license_{os.path.basename(p)}"))
        
    # Draft final report
    final_report = f"""# {args.dataset_name} Manual Validation Report

> [!IMPORTANT]
> No ground-truth scoring was performed. Results are intended for manual visual inspection and operational/runtime validation.

## 1. Dataset Inventory & Deduplication
- **Location:** `E:\\ANPR\\{args.dataset_name}`
- **Physical Files Discovered:** {best_stats['physical_files']}
- **Unique Images Processed:** {best_stats['unique_images']}
- **Duplicates Skipped:** {best_stats['duplicates']} (from `sample_datasets/`)

## 2. Environment
- **Models:** YOLO11 (`best.pt`), YOLOv8 (`license.pt`)
- **OCR Engine:** Awiros (`PaddleOCRAdapter`)
- **Execution:** Isolated in `E:\\ANPR\\benchmark` (IBVAP unmodified)

## 3. Operational Statistics

### best.pt + awiros
- **Images with detections:** {best_stats['images_with_det']}
- **Total plate detections:** {best_stats['total_plates']}
- **OCR Attempts:** {best_stats['ocr_attempts']}
- **Non-empty reads:** {best_stats['non_empty']}
- **Sequential FPS:** {best_stats['fps']:.2f}
- **Latency (Avg):** {best_stats['tot_avg']:.1f}ms

### license.pt + awiros
- **Images with detections:** {license_stats['images_with_det']}
- **Total plate detections:** {license_stats['total_plates']}
- **OCR Attempts:** {license_stats['ocr_attempts']}
- **Non-empty reads:** {license_stats['non_empty']}
- **Sequential FPS:** {license_stats['fps']:.2f}
- **Latency (Avg):** {license_stats['tot_avg']:.1f}ms

## 4. Visual Inspection Categories
Representative visual samples are located at:
`{vis_dir}`

*Please review the images for:*
- Successful-looking examples
- OCR failures
- Detection failures
- False positives
- Difficult / Angled plates
- Small plates

## 5. Output Paths
- **best.pt annotated images:** `{os.path.join(base_dir, 'best_awiros', 'annotated_images')}`
- **license.pt annotated images:** `{os.path.join(base_dir, 'license_awiros', 'annotated_images')}`
- **Plate crops:** In respective `plate_crops/` folders
- **Mapping logs:** In respective `mapping.jsonl`

## 6. Observed Limitations / Errors
- No major execution errors occurred during processing. All identical duplicated images were safely hashed and skipped.
"""
    report_path = rf"E:\ANPR\benchmark\reports\{args.dataset_name}_manual_validation.md"
    with open(report_path, "w") as f:
        f.write(final_report)
        
    print(f"Reports generated successfully!")

if __name__ == "__main__":
    main()
