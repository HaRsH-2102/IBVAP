import os
import json
import csv
import cv2
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

def main():
    gt_csv = r"E:\ANPR\benchmark\ground_truth\state_wise_olx_gt.csv"
    img_dir = r"E:\ANPR\State-wise_OLX"
    json_file = r"E:\ANPR\benchmark\results\State-wise_OLX_best_easyocr.json"
    out_dir = r"E:\ANPR\benchmark\results\state_wise_olx\visualizations"
    
    os.makedirs(out_dir, exist_ok=True)
    
    gt_dict = {}
    with open(gt_csv, "r") as f:
        for row in csv.DictReader(f):
            if row["image_path"] not in gt_dict:
                gt_dict[row["image_path"]] = []
            gt_dict[row["image_path"]].append(row)
            
    with open(json_file, "r") as f:
        data = json.load(f)
        
    generated = 0
    
    # Try to find a mix of successes and failures
    for img_res in data:
        if generated >= 20: break
        
        img_name = img_res["image"]
        
        # Find matching GT key
        # json only has basename, gt has relative path
        gt_key = None
        for k in gt_dict.keys():
            if os.path.basename(k) == img_name:
                gt_key = k
                break
                
        if not gt_key: continue
        
        gt_objects = gt_dict[gt_key]
        preds = img_res.get("plates", [])
        
        img_path = os.path.join(img_dir, gt_key)
        img = cv2.imread(img_path)
        if img is None: continue
        
        for g in gt_objects:
            gt_box = [int(g["x1"]), int(g["y1"]), int(g["x2"]), int(g["y2"])]
            gt_text = g["ground_truth_plate"]
            gt_norm = normalize_text(gt_text)
            
            best_iou = 0
            best_p = None
            
            for p in preds:
                iou = bb_iou(p["box"], gt_box)
                if iou > best_iou:
                    best_iou = iou
                    best_p = p
                    
            status = "SUCCESS"
            pred_text = ""
            pred_conf = 0.0
            
            if best_iou < 0.50:
                status = "DETECTION_FAILURE"
            else:
                pred_text = best_p["text"]
                pred_norm = normalize_text(pred_text)
                pred_conf = best_p.get("confidence", 0.0)
                if pred_norm != gt_norm:
                    status = "OCR_FAILURE"
                    
            color = (0, 255, 0) if status == "SUCCESS" else (0, 0, 255)
            
            # Draw GT box (blue)
            cv2.rectangle(img, (gt_box[0], gt_box[1]), (gt_box[2], gt_box[3]), (255, 0, 0), 2)
            cv2.putText(img, f"GT: {gt_text}", (gt_box[0], max(0, gt_box[1] - 30)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            if best_p:
                p_box = best_p["box"]
                # Draw Pred box
                cv2.rectangle(img, (p_box[0], p_box[1]), (p_box[2], p_box[3]), color, 2)
                cv2.putText(img, f"PR: {pred_text} ({best_iou:.2f})", (p_box[0], max(0, p_box[1] - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Overlay info
            cv2.putText(img, f"Status: {status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(img, f"Det Latency: {img_res.get('det_time_ms',0):.1f}ms", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            if best_p:
                cv2.putText(img, f"OCR Latency: {best_p.get('ocr_time_ms',0):.1f}ms", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
            out_path = os.path.join(out_dir, f"{status}_{img_name}")
            cv2.imwrite(out_path, img)
            generated += 1
            break # one per image
            
    print(f"Generated {generated} visualizations in {out_dir}")

if __name__ == "__main__":
    main()
