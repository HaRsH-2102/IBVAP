import os
import csv
import cv2
import time
import re
import numpy as np
from difflib import SequenceMatcher

import sys
sys.path.append(r"E:\ANPR\benchmark")
from adapters.easyocr_adapter import EasyOCRAdapter
from adapters.paddleocr_adapter import PaddleOCRAdapter

def normalize_text(text):
    if not text: return ""
    text = text.upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text

def calculate_cer(pred, gt):
    if len(gt) == 0:
        return 1.0 if len(pred) > 0 else 0.0
    # Levenshtein distance simplified using SequenceMatcher
    matcher = SequenceMatcher(None, pred, gt)
    distance = sum(block.size for block in matcher.get_matching_blocks())
    errors = max(len(pred), len(gt)) - distance
    return errors / len(gt)

def calculate_char_acc(pred, gt):
    if len(gt) == 0: return 0.0
    matcher = SequenceMatcher(None, pred, gt)
    return sum(block.size for block in matcher.get_matching_blocks()) / max(len(pred), len(gt))

def main():
    crop_dir = r"E:\ANPR\benchmark\results\state_wise_olx\gt_plate_crops"
    crop_csv_path = os.path.join(crop_dir, "crop_mapping.csv")
    
    if not os.path.exists(crop_csv_path):
        print("Crop mapping not found")
        return
        
    crops = []
    with open(crop_csv_path, "r") as f:
        crops = list(csv.DictReader(f))
        
    print("Loading OCR engines...")
    easyocr = EasyOCRAdapter()
    awiros = PaddleOCRAdapter(r"e:\ANPR\environments\paddle\python.exe", r"e:\ANPR\models\Awiros-ANPR-OCR\test.py", is_awiros=True)
    
    engines = {"easyocr": easyocr, "awiros": awiros}
    results = {"easyocr": [], "awiros": []}
    
    for row in crops:
        img_path = os.path.join(crop_dir, row["crop_path"])
        img = cv2.imread(img_path)
        gt_raw = row["ground_truth_plate"]
        gt_norm = normalize_text(gt_raw)
        
        for name, engine in engines.items():
            t0 = time.time()
            try:
                res = engine.recognize(img)
            except Exception as e:
                res = []
            latency = time.time() - t0
            
            combined_text = ""
            conf = 0.0
            if res:
                if isinstance(res, list):
                    combined_text = " ".join([r.get('text', r.get('prediction', '')) for r in res])
                    conf = np.mean([r.get('confidence', 0.0) for r in res])
                else:
                    combined_text = res.get('prediction', '')
                    conf = res.get('confidence', 0.0)
                    
            pred_raw = combined_text
            pred_norm = normalize_text(pred_raw)
            
            exact_match = (pred_raw == gt_raw)
            norm_match = (pred_norm == gt_norm)
            char_acc = calculate_char_acc(pred_norm, gt_norm)
            cer = calculate_cer(pred_norm, gt_norm)
            
            results[name].append({
                "crop_path": row["crop_path"],
                "gt_raw": gt_raw,
                "gt_norm": gt_norm,
                "pred_raw": pred_raw,
                "pred_norm": pred_norm,
                "confidence": conf,
                "latency_ms": latency * 1000,
                "exact_match": exact_match,
                "norm_match": norm_match,
                "char_acc": char_acc,
                "cer": cer
            })

    # Generate Report
    report = "# State-wise_OLX OCR-Only Evaluation\n\n"
    report += "Evaluated on perfectly cropped ground-truth plates.\n\n"
    
    report += "| OCR Engine | Total Plates | Empty Reads | Exact Match (Raw) | Exact Match (Norm) | Char Acc | CER | Avg Latency (ms) | P50 (ms) | P95 (ms) |\n"
    report += "|---|---|---|---|---|---|---|---|---|---|\n"
    
    for name in engines.keys():
        res = results[name]
        total = len(res)
        empty = sum(1 for r in res if not r["pred_norm"])
        exact_raw = sum(1 for r in res if r["exact_match"]) / total if total > 0 else 0
        exact_norm = sum(1 for r in res if r["norm_match"]) / total if total > 0 else 0
        char_acc = np.mean([r["char_acc"] for r in res]) if total > 0 else 0
        cer = np.mean([r["cer"] for r in res]) if total > 0 else 0
        
        lats = [r["latency_ms"] for r in res]
        avg_lat = np.mean(lats)
        p50 = np.percentile(lats, 50)
        p95 = np.percentile(lats, 95)
        
        report += f"| {name} | {total} | {empty} | {exact_raw:.4f} | {exact_norm:.4f} | {char_acc:.4f} | {cer:.4f} | {avg_lat:.2f} | {p50:.2f} | {p95:.2f} |\n"
        
        # Save raw OCR results
        raw_csv_path = rf"E:\ANPR\benchmark\results\state_wise_olx\raw\ocr_{name}.csv"
        os.makedirs(os.path.dirname(raw_csv_path), exist_ok=True)
        with open(raw_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=res[0].keys())
            writer.writeheader()
            writer.writerows(res)
            
    report_path = r"E:\ANPR\benchmark\reports\state_wise_olx_ocr_results.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
        
    print(f"Evaluated OCR engines and wrote to {report_path}")

if __name__ == "__main__":
    main()
