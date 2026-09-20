import os
import json
import csv
import re
import numpy as np

def normalize_text(text):
    if not text: return ""
    text = text.upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text

def bb_iou(boxA, boxB):
    xA, yA, xB, yB = max(boxA[0], boxB[0]), max(boxA[1], boxB[1]), min(boxA[2], boxB[2]), min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter == 0: return 0.0
    return inter / float((boxA[2]-boxA[0])*(boxA[3]-boxA[1]) + (boxB[2]-boxB[0])*(boxB[3]-boxB[1]) - inter)

def calculate_e2e(gt_dict, pred_data, iou_thresh=0.5):
    total_gt = 0
    correct_det = 0
    ocr_matches = 0
    e2e_matches = 0
    
    det_latencies = []
    ocr_latencies = []
    
    for img_res in pred_data:
        img_name = img_res["image"]
        det_latencies.append(img_res.get("det_time_ms", 0))
        
        gt_objects = [g for g in gt_dict.values() if os.path.basename(g["image_path"]) == img_name]
        preds = img_res.get("plates", [])
        
        for p in preds:
            ocr_latencies.append(p.get("ocr_time_ms", 0))
        
        matched_pred = set()
        for g_idx, g in enumerate(gt_objects):
            total_gt += 1
            gt_box = [int(g["x1"]), int(g["y1"]), int(g["x2"]), int(g["y2"])]
            gt_text = normalize_text(g["ground_truth_plate"])
            
            best_iou = 0
            best_p_idx = -1
            
            for p_idx, p in enumerate(preds):
                if p_idx in matched_pred: continue
                iou = bb_iou(p["box"], gt_box)
                if iou > best_iou:
                    best_iou = iou
                    best_p_idx = p_idx
                    
            if best_iou >= iou_thresh:
                correct_det += 1
                matched_pred.add(best_p_idx)
                
                pred_text = normalize_text(preds[best_p_idx]["text"])
                if pred_text == gt_text:
                    ocr_matches += 1
                    e2e_matches += 1
                    
    return {
        "total_gt": total_gt,
        "correct_det": correct_det,
        "ocr_matches": ocr_matches,
        "e2e_matches": e2e_matches,
        "det_lat": det_latencies,
        "ocr_lat": ocr_latencies
    }

def main():
    gt_csv = r"E:\ANPR\benchmark\ground_truth\state_wise_olx_gt.csv"
    gt_dict = {}
    with open(gt_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gt_dict[row["image_path"] + "_" + row["plate_id"]] = row
            
    results_dir = r"E:\ANPR\benchmark\results"
    
    # Models evaluated previously
    combinations = [
        ("best", "easyocr"),
        ("best", "awiros"),
        ("license", "easyocr"),
        ("license", "awiros"),
        ("ANPR2", "easyocr"),
        ("ANPR2", "awiros")
    ]
    
    report = "# State-wise_OLX End-to-End Evaluation\n\n"
    report += "| Detector | OCR | GT Plates | Correct Det | OCR Match | E2E Match | E2E Acc |\n"
    report += "|---|---|---|---|---|---|---|\n"
    
    latency_report = "# True Measured Latency Audit\n\n"
    latency_report += "This audit uses ACTUAL MEASURED runtime. No theoretical I/O overhead is assumed.\n\n"
    latency_report += "| Pipeline | Det Avg (ms) | Det P95 (ms) | OCR Avg (ms) | OCR P95 (ms) | Total Avg Pipeline (ms) | Sequential FPS |\n"
    latency_report += "|---|---|---|---|---|---|---|\n"
    
    for det, ocr in combinations:
        json_file = os.path.join(results_dir, f"State-wise_OLX_{det}_{ocr}.json")
        if not os.path.exists(json_file):
            continue
            
        with open(json_file, "r") as f:
            data = json.load(f)
            
        res = calculate_e2e(gt_dict, data)
        e2e_acc = res["e2e_matches"] / res["total_gt"] if res["total_gt"] > 0 else 0
        
        report += f"| {det} | {ocr} | {res['total_gt']} | {res['correct_det']} | {res['ocr_matches']} | {res['e2e_matches']} | {e2e_acc:.4f} |\n"
        
        if len(res["det_lat"]) > 0:
            avg_det = np.mean(res["det_lat"])
            p95_det = np.percentile(res["det_lat"], 95)
        else:
            avg_det, p95_det = 0, 0
            
        if len(res["ocr_lat"]) > 0:
            avg_ocr = np.mean(res["ocr_lat"])
            p95_ocr = np.percentile(res["ocr_lat"], 95)
            # OCR is per plate. Average plates per image is ~1
            plates_per_img = len(res["ocr_lat"]) / len(res["det_lat"])
            total_ocr_per_frame = avg_ocr * plates_per_img
        else:
            avg_ocr, p95_ocr = 0, 0
            total_ocr_per_frame = 0
            
        total_latency = avg_det + total_ocr_per_frame
        fps = 1000 / total_latency if total_latency > 0 else 0
        
        latency_report += f"| {det} + {ocr} | {avg_det:.2f} | {p95_det:.2f} | {avg_ocr:.2f} | {p95_ocr:.2f} | {total_latency:.2f} | {fps:.2f} |\n"
        
    e2e_path = r"E:\ANPR\benchmark\reports\state_wise_olx_end_to_end_results.md"
    lat_path = r"E:\ANPR\benchmark\reports\latency_audit.md"
    
    with open(e2e_path, "w") as f:
        f.write(report)
        
    with open(lat_path, "w") as f:
        f.write(latency_report)
        
    print("E2E and Latency evaluated!")

if __name__ == "__main__":
    main()
