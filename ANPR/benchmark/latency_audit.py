import os
import glob
import json
import numpy as np

def main():
    results_dir = r"e:\ANPR\benchmark\results"
    json_files = glob.glob(os.path.join(results_dir, "*.json"))
    
    report = "# ANPR Latency Audit\n\n"
    report += "Latency is calculated per frame sequentially. Total Latency = Avg Detection Time + (Avg Plates per Image * Avg OCR Time) + Assumed I/O Overhead (15ms). FPS = 1000 / Total Latency.\n\n"
    report += "| Dataset | Detector | OCR | Avg Det (ms) | Avg OCR (ms) | Plates/Img | Total Latency (ms) | FPS |\n"
    report += "|---|---|---|---|---|---|---|---|\n"

    for jf in json_files:
        name_parts = os.path.basename(jf).replace(".json", "").split("_")
        ocr_engine = name_parts[-1]
        detector = name_parts[-2]
        dataset = "_".join(name_parts[:-2])
        
        with open(jf, "r") as f:
            data = json.load(f)
            
        total_images = len(data)
        total_plates = sum(len(img["plates"]) for img in data)
        plates_per_img = total_plates / total_images if total_images > 0 else 0
        
        det_times = [img.get("det_time_ms", 0) for img in data if "det_time_ms" in img]
        
        ocr_times = []
        for img in data:
            for p in img["plates"]:
                if "ocr_time_ms" in p:
                    ocr_times.append(p["ocr_time_ms"])
        
        if not det_times:
            continue
            
        avg_det = np.mean(det_times)
        avg_ocr = np.mean(ocr_times) if ocr_times else 0.0
        
        io_overhead = 15.0 # Typical image read + CV2 operations
        total_latency = avg_det + (plates_per_img * avg_ocr) + io_overhead
        fps = 1000.0 / total_latency if total_latency > 0 else 0
        
        report += f"| {dataset} | {detector} | {ocr_engine} | {avg_det:.2f} | {avg_ocr:.2f} | {plates_per_img:.2f} | {total_latency:.2f} | {fps:.2f} |\n"

    report_path = r"e:\ANPR\reports\latency_audit.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
        
    print(f"Latency audit saved to {report_path}")

if __name__ == "__main__":
    main()
