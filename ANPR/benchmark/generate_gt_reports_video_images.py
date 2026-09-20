import os
import json

def main():
    base_dir = r"E:\ANPR\benchmark\results\video_images_gt_validation\20260917_163536"
    reports_dir = r"E:\ANPR\benchmark\reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    best_stats_path = os.path.join(base_dir, "best_awiros", "stats.json")
    license_stats_path = os.path.join(base_dir, "license_awiros", "stats.json")
    
    with open(best_stats_path, "r") as f:
        best_stats = json.load(f)
    with open(license_stats_path, "r") as f:
        license_stats = json.load(f)
        
    models = [best_stats, license_stats]
    
    # 1. Detector Results
    det_md = "# video_images Detector Benchmark Results\n\n"
    det_md += "| Model | IoU Threshold | TP | FP | FN | Precision | Recall | F1 | mIoU |\n"
    det_md += "|---|---|---|---|---|---|---|---|---|\n"
    for s in models:
        det_md += f"| {s['model']} + awiros | 0.50 | {s['tp']} | {s['fp']} | {s['fn']} | {s['precision']:.4f} | {s['recall']:.4f} | {s['f1']:.4f} | {s['miou']:.4f} |\n"
        
    with open(os.path.join(reports_dir, "video_images_detector_results.md"), "w") as f:
        f.write(det_md)
        
    # 2. OCR Results
    ocr_md = "# video_images OCR Benchmark Results\n\n"
    ocr_md += "| Model | Raw Exact Match | Normalized Exact Match | Character Accuracy | CER |\n"
    ocr_md += "|---|---|---|---|---|\n"
    for s in models:
        ocr_md += f"| {s['model']} + awiros | {s['ocr_raw_acc']:.4f} | {s['ocr_norm_acc']:.4f} | {s['char_acc']:.4f} | {s['cer']:.4f} |\n"
        
    with open(os.path.join(reports_dir, "video_images_ocr_results.md"), "w") as f:
        f.write(ocr_md)
        
    # 3. E2E Results
    e2e_md = "# video_images End-to-End Benchmark Results\n\n"
    e2e_md += "| Model | Detection Recall | OCR Accuracy Given Detection | E2E Exact Match |\n"
    e2e_md += "|---|---|---|---|\n"
    for s in models:
        e2e_md += f"| {s['model']} + awiros | {s['recall']:.4f} | {s['ocr_norm_acc']:.4f} | {s['e2e_acc']:.4f} |\n"
        
    with open(os.path.join(reports_dir, "video_images_end_to_end_results.md"), "w") as f:
        f.write(e2e_md)
        
    # 4. Final Benchmark Report
    final_md = "# video_images Final Benchmark Report (True GT)\n\n"
    final_md += "> [!IMPORTANT]\n> This benchmark uses TRUE Ground-Truth extracted from Pascal VOC XML annotations.\n\n"
    final_md += "## Dataset\n"
    final_md += "- **Path:** `E:\\ANPR\\video_images`\n"
    final_md += "- **Source Images:** 654\n"
    final_md += "- **GT Images (XML):** 654\n"
    final_md += "- **Matched Images:** 654\n"
    final_md += "- **Missing GT:** 0\n"
    final_md += "- **Format:** Pascal VOC Bounding Box & Text\n\n"
    
    final_md += "## Latency Metrics\n"
    final_md += "| Model | Det Avg ms | Det P50 ms | Det P95 ms | OCR Avg ms | OCR P50 ms | OCR P95 ms | Total Avg ms | FPS |\n"
    final_md += "|---|---|---|---|---|---|---|---|---|\n"
    for s in models:
        final_md += f"| {s['model']} + awiros | {s['det_avg']:.1f} | {s['det_p50']:.1f} | {s['det_p95']:.1f} | {s['ocr_avg']:.1f} | {s['ocr_p50']:.1f} | {s['ocr_p95']:.1f} | {s['tot_avg']:.1f} | {s['fps']:.2f} |\n"
        
    final_md += "\n## Dataset Leakage Warning\n"
    final_md += "> [!WARNING]\n> **TRAINING OVERLAP UNKNOWN:** It cannot be definitively confirmed if these models were independently trained from this dataset.\n"
    
    with open(os.path.join(reports_dir, "video_images_final_benchmark_report.md"), "w") as f:
        f.write(final_md)
        
    print("GT Reports generated successfully!")

if __name__ == "__main__":
    main()
