import os
import glob
import json
import numpy as np

def main():
    results_dir = r"e:\ANPR\benchmark\results"
    json_files = glob.glob(os.path.join(results_dir, "*.json"))
    
    report = "# ANPR Quantitative Performance Report\n\n"
    report += "| Dataset | Detector | OCR | Images Processed | Plates Found | Avg Det Time (ms) | Avg OCR Time (ms) |\n"
    report += "|---|---|---|---|---|---|---|\n"

    for jf in json_files:
        name_parts = os.path.basename(jf).replace(".json", "").split("_")
        # e.g., State-wise_OLX_license_easyocr
        # Name can have underscores so we parse backwards
        ocr_engine = name_parts[-1]
        detector = name_parts[-2]
        dataset = "_".join(name_parts[:-2])
        
        with open(jf, "r") as f:
            data = json.load(f)
            
        total_images = len(data)
        total_plates = sum(len(img["plates"]) for img in data)
        
        det_times = [img.get("det_time_ms", 0) for img in data if "det_time_ms" in img]
        
        ocr_times = []
        for img in data:
            for p in img["plates"]:
                if "ocr_time_ms" in p:
                    ocr_times.append(p["ocr_time_ms"])
        
        avg_det = round(np.mean(det_times), 2) if det_times else "N/A"
        avg_ocr = round(np.mean(ocr_times), 2) if ocr_times else "N/A"
        
        report += f"| {dataset} | {detector} | {ocr_engine} | {total_images} | {total_plates} | {avg_det} | {avg_ocr} |\n"

    report_path = r"e:\ANPR\reports\quantitative_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
        
    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    main()
