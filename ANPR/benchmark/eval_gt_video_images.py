import os
import csv
import json
import argparse
import re
import cv2
import Levenshtein
import numpy as np
from datetime import datetime
from ultralytics import YOLO

# OCR imports
import subprocess
import tempfile
import time

def normalize_text(text):
    if not text: return ""
    text = text.upper()
    return re.sub(r'[^A-Z0-9]', '', text)

def bb_iou(boxA, boxB):
    xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
    xB, yB = min(boxA[2], boxB[2]), min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter == 0: return 0.0
    boxAArea = (boxA[2]-boxA[0])*(boxA[3]-boxA[1])
    boxBArea = (boxB[2]-boxB[0])*(boxB[3]-boxB[1])
    return inter / float(boxAArea + boxBArea - inter)

def draw_visualizations(img_path, gt_boxes, gt_texts, preds, matches, out_path):
    img = cv2.imread(img_path)
    if img is None: return
    
    # Draw GT
    for gbox, gtext in zip(gt_boxes, gt_texts):
        cv2.rectangle(img, (int(gbox[0]), int(gbox[1])), (int(gbox[2]), int(gbox[3])), (255, 0, 0), 2)
        cv2.putText(img, f"GT: {gtext}", (int(gbox[0]), max(10, int(gbox[1])-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
    # Draw Preds
    for p, match in zip(preds, matches):
        pbox = p['bbox']
        color = (0, 255, 0) if match['e2e_correct'] else ((0, 255, 255) if match['det_correct'] else (0, 0, 255))
        cv2.rectangle(img, (int(pbox[0]), int(pbox[1])), (int(pbox[2]), int(pbox[3])), color, 2)
        
        status_text = f"P: {p.get('raw_ocr', '')} ({p.get('conf', 0.0):.2f})"
        cv2.putText(img, status_text, (int(pbox[0]), int(pbox[3])+20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        iou_text = f"IoU: {match['iou']:.2f}"
        cv2.putText(img, iou_text, (int(pbox[0]), int(pbox[3])+40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
    cv2.imwrite(out_path, img)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, choices=["best", "license"])
    parser.add_argument("--out_dir", type=str, required=True)
    args = parser.parse_args()
    
    dataset_dir = r"E:\ANPR\video_images"
    gt_mapping_path = r"E:\ANPR\benchmark\ground_truth\video_images_gt_mapping.csv"
    
    out_dir = os.path.join(args.out_dir, f"{args.model}_awiros")
    vis_dir = os.path.join(out_dir, "visualizations")
    crop_dir = os.path.join(out_dir, "plate_crops")
    os.makedirs(vis_dir, exist_ok=True)
    os.makedirs(crop_dir, exist_ok=True)
    
    if args.model == "best":
        model_path = r"E:\ANPR\Auto-Num-Plate-Recognition\best.pt"
    else:
        model_path = r"E:\ANPR\ANPR-Indian-License-Plate-Detection\license.pt"
    model = YOLO(model_path)
    
    gt_data = []
    with open(gt_mapping_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] == "OK":
                plates = []
                for p in row["plates"].split(";"):
                    if p:
                        name, box_str = p.split("|")
                        x1, y1, x2, y2 = map(int, box_str.split(","))
                        plates.append({"text": name, "bbox": [x1, y1, x2, y2]})
                row["parsed_plates"] = plates
                gt_data.append(row)
                
    results_log = []
    
    total_gt_plates = sum(len(g["parsed_plates"]) for g in gt_data)
    total_det_correct = 0
    total_ocr_raw_correct = 0
    total_ocr_norm_correct = 0
    total_e2e_correct = 0
    total_preds = 0
    total_chars = 0
    total_char_errors = 0
    iou_sum = 0
    
    det_latencies = []
    ocr_latencies = []
    
    vis_count = 0
    
    # Prepare batch OCR processing to save time
    # But wait, to keep it simple and track latencies per crop, I can use the same batcher approach
    # Let's crop all first
    print("Running detection and cropping...")
    
    crop_data = []
    for g in gt_data:
        img_path = g["source_image"]
        img = cv2.imread(img_path)
        if img is None: continue
        
        t0 = time.time()
        res = model(img, verbose=False)[0]
        det_time = (time.time() - t0) * 1000
        det_latencies.append(det_time)
        
        preds = []
        for i, box in enumerate(res.boxes):
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            
            crop_path = os.path.join(crop_dir, f"{os.path.basename(img_path)}_{i}.jpg")
            crop = img[int(y1):int(y2), int(x1):int(x2)]
            if crop.size > 0:
                cv2.imwrite(crop_path, crop)
                crop_data.append({"img_path": img_path, "crop_path": crop_path, "bbox": [x1, y1, x2, y2], "conf": conf, "det_time": det_time, "g": g})
                preds.append({"bbox": [x1, y1, x2, y2], "conf": conf, "crop_path": crop_path})
                
    print(f"Total crops generated: {len(crop_data)}")
    
    ocr_res_file = os.path.join(out_dir, "batch_results.json")
    paddle_env = r"e:\ANPR\environments\paddle\python.exe"
    awiros_script = r"E:\ANPR\benchmark\run_awiros_batch.py"
    subprocess.run([paddle_env, awiros_script, crop_dir, ocr_res_file])
    
    with open(ocr_res_file, "r") as f:
        ocr_results = json.load(f)
        
    for c in crop_data:
        # Match crop basename since batch OCR keys are just basenames
        crop_basename = os.path.basename(c['crop_path'])
        c_res = ocr_results.get(crop_basename, {})
        c['raw_ocr'] = c_res.get('text', '')
        c['ocr_conf'] = c_res.get('confidence', 0.0)
        c['ocr_time'] = c_res.get('ocr_time_ms', 0.0)
        ocr_latencies.append(c['ocr_time'])
        
    # Group back to images and evaluate
    grouped = {}
    for c in crop_data:
        grouped.setdefault(c["img_path"], []).append(c)
        
    for g in gt_data:
        img_path = g["source_image"]
        preds = grouped.get(img_path, [])
        total_preds += len(preds)
        
        gt_boxes = [p["bbox"] for p in g["parsed_plates"]]
        gt_texts = [p["text"] for p in g["parsed_plates"]]
        
        matches = []
        for p in preds:
            best_iou = 0
            best_gt_idx = -1
            for g_idx, gbox in enumerate(gt_boxes):
                iou = bb_iou(p["bbox"], gbox)
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = g_idx
            
            p_dict = {
                "bbox": p["bbox"],
                "det_conf": p["conf"],
                "raw_ocr": p["raw_ocr"],
                "norm_ocr": normalize_text(p["raw_ocr"]),
                "ocr_conf": p["ocr_conf"],
                "det_time": p["det_time"],
                "ocr_time": p["ocr_time"]
            }
            
            match_dict = {
                "iou": best_iou,
                "gt_matched": best_gt_idx,
                "det_correct": best_iou >= 0.50,
                "ocr_raw_correct": False,
                "ocr_norm_correct": False,
                "e2e_correct": False,
                "cer": 0.0
            }
            
            if best_iou >= 0.50 and best_gt_idx != -1:
                total_det_correct += 1
                iou_sum += best_iou
                gt_text = gt_texts[best_gt_idx]
                norm_gt = normalize_text(gt_text)
                
                if p_dict["raw_ocr"] == gt_text:
                    match_dict["ocr_raw_correct"] = True
                    total_ocr_raw_correct += 1
                if p_dict["norm_ocr"] == norm_gt:
                    match_dict["ocr_norm_correct"] = True
                    total_ocr_norm_correct += 1
                    match_dict["e2e_correct"] = True
                    total_e2e_correct += 1
                    
                dist = Levenshtein.distance(p_dict["norm_ocr"], norm_gt)
                match_dict["cer"] = dist / max(len(norm_gt), 1)
                total_char_errors += dist
                total_chars += len(norm_gt)
                
            matches.append(match_dict)
            
            results_log.append({
                "source_image": img_path,
                "crop_path": p["crop_path"],
                "bbox": p_dict["bbox"],
                "det_conf": p_dict["det_conf"],
                "raw_ocr": p_dict["raw_ocr"],
                "norm_ocr": p_dict["norm_ocr"],
                "ocr_conf": p_dict["ocr_conf"],
                "det_time_ms": p_dict["det_time"],
                "ocr_time_ms": p_dict["ocr_time"],
                "matched_gt_text": gt_texts[best_gt_idx] if best_gt_idx != -1 else None,
                "iou": best_iou,
                "e2e_correct": match_dict["e2e_correct"]
            })
            
        if vis_count < 30 or any(not m["e2e_correct"] for m in matches):
            if vis_count < 100:
                vis_path = os.path.join(vis_dir, os.path.basename(img_path))
                draw_visualizations(img_path, gt_boxes, gt_texts, preds, matches, vis_path)
                vis_count += 1
                
    # Calculate final metrics
    precision = total_det_correct / total_preds if total_preds > 0 else 0
    recall = total_det_correct / total_gt_plates if total_gt_plates > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    miou = iou_sum / total_det_correct if total_det_correct > 0 else 0
    
    ocr_raw_acc = total_ocr_raw_correct / total_det_correct if total_det_correct > 0 else 0
    ocr_norm_acc = total_ocr_norm_correct / total_det_correct if total_det_correct > 0 else 0
    cer = total_char_errors / total_chars if total_chars > 0 else 0
    char_acc = max(0, 1.0 - cer)
    
    e2e_acc = total_e2e_correct / total_gt_plates if total_gt_plates > 0 else 0
    
    det_avg = np.mean(det_latencies) if det_latencies else 0
    det_p50 = np.percentile(det_latencies, 50) if det_latencies else 0
    det_p95 = np.percentile(det_latencies, 95) if det_latencies else 0
    ocr_avg = np.mean(ocr_latencies) if ocr_latencies else 0
    ocr_p50 = np.percentile(ocr_latencies, 50) if ocr_latencies else 0
    ocr_p95 = np.percentile(ocr_latencies, 95) if ocr_latencies else 0
    tot_avg = det_avg + ocr_avg
    fps = 1000.0 / tot_avg if tot_avg > 0 else 0
    
    stats = {
        "model": args.model,
        "images": len(gt_data),
        "total_gt_plates": total_gt_plates,
        "total_preds": total_preds,
        "tp": total_det_correct,
        "fp": total_preds - total_det_correct,
        "fn": total_gt_plates - total_det_correct,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "miou": miou,
        "ocr_raw_acc": ocr_raw_acc,
        "ocr_norm_acc": ocr_norm_acc,
        "char_acc": char_acc,
        "cer": cer,
        "e2e_acc": e2e_acc,
        "det_avg": det_avg,
        "det_p50": det_p50,
        "det_p95": det_p95,
        "ocr_avg": ocr_avg,
        "ocr_p50": ocr_p50,
        "ocr_p95": ocr_p95,
        "tot_avg": tot_avg,
        "fps": fps
    }
    
    with open(os.path.join(out_dir, "mapping.jsonl"), "w") as f:
        for r in results_log:
            f.write(json.dumps(r) + "\n")
            
    with open(os.path.join(out_dir, "stats.json"), "w") as f:
        json.dump(stats, f, indent=4)
        
    print(f"Completed {args.model}. Results in {out_dir}")

if __name__ == "__main__":
    main()
