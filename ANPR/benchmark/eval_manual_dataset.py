import os
import sys
import json
import hashlib
import time
import cv2
import argparse
import subprocess
import numpy as np
from datetime import datetime
from ultralytics import YOLO

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def normalize_text(text):
    if not text: return ""
    import re
    return re.sub(r'[^A-Z0-9]', '', text.upper())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, choices=["best", "license"])
    parser.add_argument("--out_dir", type=str, default="")
    parser.add_argument("--input", type=str, required=True, help="Path to the dataset directory")
    args = parser.parse_args()
    
    dataset_dir = args.input
    dataset_name = os.path.basename(os.path.normpath(dataset_dir))
    
    if args.out_dir:
        out_dir = os.path.join(args.out_dir, f"{args.model}_awiros")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = rf"E:\ANPR\benchmark\results\{dataset_name}_validation\{timestamp}\{args.model}_awiros"
    
    annot_dir = os.path.join(out_dir, "annotated_images")
    crop_dir = os.path.join(out_dir, "plate_crops")
    log_dir = os.path.join(out_dir, "logs")
    os.makedirs(annot_dir, exist_ok=True)
    os.makedirs(crop_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    # 1. Discover and deduplicate
    print("Discovering images...")
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    all_files = []
    for root, _, files in os.walk(dataset_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_exts:
                all_files.append(os.path.join(root, f))
                
    unique_images = []
    seen_hashes = set()
    skipped_count = 0
    failed_count = 0
    
    for f in all_files:
        try:
            h = compute_sha256(f)
            if h in seen_hashes:
                skipped_count += 1
            else:
                seen_hashes.add(h)
                unique_images.append(f)
        except Exception as e:
            print(f"Failed to read {f}: {e}")
            failed_count += 1
            
    print(f"Physical images: {len(all_files)}")
    print(f"Unique images: {len(unique_images)}")
    print(f"Duplicates skipped: {skipped_count}")
    
    # 2. YOLO Detection
    if args.model == "best":
        model_path = r"E:\ANPR\Auto-Num-Plate-Recognition\best.pt"
    else:
        model_path = r"E:\ANPR\ANPR-Indian-License-Plate-Detection\license.pt"
    
    model = YOLO(model_path)
    
    detections_mapping = []
    
    for img_idx, img_path in enumerate(unique_images):
        img = cv2.imread(img_path)
        if img is None:
            failed_count += 1
            continue
            
        t0 = time.perf_counter()
        results = model(img, verbose=False)
        det_time_ms = (time.perf_counter() - t0) * 1000.0
        
        plates = []
        for r in results:
            boxes = r.boxes
            for i in range(len(boxes)):
                box = boxes.xyxy[i].cpu().numpy().astype(int)
                conf = float(boxes.conf[i].cpu().numpy())
                
                x1, y1, x2, y2 = box
                crop = img[y1:y2, x1:x2]
                if crop.shape[0] == 0 or crop.shape[1] == 0: continue
                
                crop_name = f"img_{img_idx}_plate_{i}.jpg"
                crop_path = os.path.join(crop_dir, crop_name)
                cv2.imwrite(crop_path, crop)
                
                plates.append({
                    "crop_name": crop_name,
                    "crop_path": crop_path,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "conf": conf
                })
                
        detections_mapping.append({
            "source_image": img_path,
            "filename": os.path.basename(img_path),
            "det_time_ms": det_time_ms,
            "plates": plates
        })
        
    # 3. Run PaddleOCR Batched
    ocr_out_json = os.path.join(log_dir, "ocr_results.json")
    paddle_env = r"e:\ANPR\environments\paddle\python.exe"
    awiros_script = r"E:\ANPR\benchmark\run_awiros_batch.py"
    cmd = [paddle_env, awiros_script, crop_dir, ocr_out_json]
    
    print(f"Running Awiros OCR on {sum(len(d['plates']) for d in detections_mapping)} crops...")
    subprocess.run(cmd)
    
    ocr_results = {}
    if os.path.exists(ocr_out_json):
        with open(ocr_out_json, "r") as f:
            ocr_results = json.load(f)
            
    # 4. Annotation and Metrics
    total_images_with_dets = 0
    total_plates = 0
    non_empty_ocr = 0
    empty_ocr = 0
    
    det_latencies = []
    ocr_latencies = []
    total_latencies = []
    
    final_mappings = []
    
    for item in detections_mapping:
        img_path = item["source_image"]
        img = cv2.imread(img_path)
        det_time_ms = item["det_time_ms"]
        det_latencies.append(det_time_ms)
        
        has_det = False
        img_ocr_latencies = []
        
        for p in item["plates"]:
            has_det = True
            total_plates += 1
            crop_name = p["crop_name"]
            
            raw_text = ""
            ocr_conf = 0.0
            ocr_time_ms = 0.0
            
            if crop_name in ocr_results:
                ocr_res = ocr_results[crop_name]
                raw_text = ocr_res.get("text", "")
                ocr_conf = ocr_res.get("confidence", 0.0)
                ocr_time_ms = ocr_res.get("ocr_time_ms", 0.0)
                
            norm_text = normalize_text(raw_text)
            if norm_text:
                non_empty_ocr += 1
                display_text = norm_text
            else:
                empty_ocr += 1
                display_text = "FAILED/EMPTY"
                
            img_ocr_latencies.append(ocr_time_ms)
            ocr_latencies.append(ocr_time_ms)
            
            p["raw_ocr"] = raw_text
            p["normalized_ocr"] = norm_text
            p["ocr_confidence"] = ocr_conf
            p["ocr_time_ms"] = ocr_time_ms
            
            # Annotate
            x1, y1, x2, y2 = p["bbox"]
            color = (0, 255, 0) if norm_text else (0, 0, 255)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            label_det = f"DET: {p['conf']:.2f}"
            label_ocr = f"OCR: {display_text} ({ocr_conf:.2f})" if norm_text else "OCR: FAILED"
            
            cv2.putText(img, label_det, (x1, max(20, y1 - 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.putText(img, label_ocr, (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
        if has_det:
            total_images_with_dets += 1
            
        img_total_lat = det_time_ms + sum(img_ocr_latencies)
        total_latencies.append(img_total_lat)
        
        cv2.putText(img, f"File: {item['filename']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Lat: Det {det_time_ms:.1f}ms | OCR {sum(img_ocr_latencies):.1f}ms", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        out_img_path = os.path.join(annot_dir, item["filename"])
        cv2.imwrite(out_img_path, img)
        
        item["total_latency_ms"] = img_total_lat
        item["output_image"] = out_img_path
        final_mappings.append(item)
        
    with open(os.path.join(out_dir, "mapping.jsonl"), "w") as f:
        for m in final_mappings:
            f.write(json.dumps(m) + "\n")
            
    # Compute stats
    def get_stats(arr):
        if not arr: return 0, 0, 0
        arr = np.array(arr)
        return float(np.mean(arr)), float(np.percentile(arr, 50)), float(np.percentile(arr, 95))
        
    det_avg, det_p50, det_p95 = get_stats(det_latencies)
    ocr_avg, ocr_p50, ocr_p95 = get_stats(ocr_latencies)
    tot_avg, tot_p50, tot_p95 = get_stats(total_latencies)
    fps = 1000.0 / tot_avg if tot_avg > 0 else 0
    
    summary = f"""# Operational Summary: {args.model} + awiros
    
Dataset Stats:
- Physical files discovered: {len(all_files)}
- Unique images processed: {len(unique_images)}
- Duplicates skipped: {skipped_count}
- Failed reads: {failed_count}

Detection Stats:
- Images with detections: {total_images_with_dets}
- Total plate detections: {total_plates}

OCR Stats (Attempts = Detections = {total_plates}):
- Non-empty reads: {non_empty_ocr}
- Empty/Failed reads: {empty_ocr}

Latency (ms):
- Det: Avg {det_avg:.1f} | P50 {det_p50:.1f} | P95 {det_p95:.1f}
- OCR: Avg {ocr_avg:.1f} | P50 {ocr_p50:.1f} | P95 {ocr_p95:.1f}
- Total Pipeline: Avg {tot_avg:.1f} | P50 {tot_p50:.1f} | P95 {tot_p95:.1f}
- Sequential FPS: {fps:.2f}

Note: No ground-truth scoring was performed. These are purely operational metrics for manual validation.
"""
    with open(os.path.join(out_dir, "summary.md"), "w") as f:
        f.write(summary)
        
    # Write a master summary JSON for the final report compiler
    stats_json = {
        "model": args.model,
        "physical_files": len(all_files),
        "unique_images": len(unique_images),
        "duplicates": skipped_count,
        "failed": failed_count,
        "images_with_det": total_images_with_dets,
        "total_plates": total_plates,
        "ocr_attempts": total_plates,
        "non_empty": non_empty_ocr,
        "det_avg": det_avg, "det_p50": det_p50, "det_p95": det_p95,
        "ocr_avg": ocr_avg, "ocr_p50": ocr_p50, "ocr_p95": ocr_p95,
        "tot_avg": tot_avg, "fps": fps,
        "out_dir": out_dir
    }
    with open(os.path.join(out_dir, "stats.json"), "w") as f:
        json.dump(stats_json, f, indent=2)

    print(f"Completed {args.model}. Results in {out_dir}")
    print(summary)

if __name__ == "__main__":
    main()
