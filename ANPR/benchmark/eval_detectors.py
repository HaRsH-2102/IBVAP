import os
import json
import csv
import glob
import numpy as np

def bb_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def evaluate_detector(gt_dict, pred_data, iou_thresh=0.5):
    tp = 0
    fp = 0
    fn = 0
    total_iou = 0.0
    iou_count = 0
    
    # We will track which GT plates are matched
    for img_res in pred_data:
        img_name = img_res["image"]
        # Find matching gt objects for this image
        # Note: gt_dict keys are the full relative path, e.g., 'AN\AN1.jpg'
        gt_objects = [g for g in gt_dict.values() if os.path.basename(g["image_path"]) == img_name]
        
        preds = img_res.get("plates", [])
        
        # Match predictions to GT deterministically (greedy highest IoU first)
        matched_gt = set()
        matched_pred = set()
        
        # Calculate all IoUs
        iou_matrix = [] # (pred_idx, gt_idx, iou)
        for p_idx, p in enumerate(preds):
            for g_idx, g in enumerate(gt_objects):
                gt_box = [int(g["x1"]), int(g["y1"]), int(g["x2"]), int(g["y2"])]
                iou = bb_iou(p["box"], gt_box)
                if iou >= iou_thresh:
                    iou_matrix.append((p_idx, g_idx, iou))
        
        # Sort by highest IoU
        iou_matrix.sort(key=lambda x: x[2], reverse=True)
        
        for p_idx, g_idx, iou in iou_matrix:
            if p_idx not in matched_pred and g_idx not in matched_gt:
                matched_pred.add(p_idx)
                matched_gt.add(g_idx)
                tp += 1
                total_iou += iou
                iou_count += 1
                
        # Unmatched predictions are FP
        fp += len(preds) - len(matched_pred)
        # Unmatched GT are FN
        fn += len(gt_objects) - len(matched_gt)
        
    # Count FN for images that the detector didn't even output a result for (if any)
    pred_images = {img_res["image"] for img_res in pred_data}
    for gt in gt_dict.values():
        if os.path.basename(gt["image_path"]) not in pred_images:
            fn += 1
            
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    miou = total_iou / iou_count if iou_count > 0 else 0
    
    return {
        "TP": tp, "FP": fp, "FN": fn,
        "Precision": precision, "Recall": recall, "F1": f1, "mIoU": miou
    }

def main():
    gt_csv = r"E:\ANPR\benchmark\ground_truth\state_wise_olx_gt.csv"
    gt_dict = {}
    total_gt = 0
    with open(gt_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gt_dict[row["image_path"] + "_" + row["plate_id"]] = row
            total_gt += 1
            
    results_dir = r"E:\ANPR\benchmark\results"
    
    detectors = ["best", "license", "ANPR2"]
    
    report = "# State-wise_OLX Detector Evaluation\n\n"
    report += "This evaluation uses exact bounding box matching against Pascal VOC XML ground truth.\n\n"
    report += "| Detector | IoU | TP | FP | FN | Precision | Recall | F1 | mIoU | GT Plates | Pred Instances |\n"
    report += "|---|---|---|---|---|---|---|---|---|---|---|\n"
    
    for det in detectors:
        # Load one of the JSONs for this detector (they have identical detection outputs)
        json_file = os.path.join(results_dir, f"State-wise_OLX_{det}_easyocr.json")
        if not os.path.exists(json_file):
            continue
            
        with open(json_file, "r") as f:
            data = json.load(f)
            
        total_pred = sum(len(img["plates"]) for img in data)
        
        # Evaluate at IoU 0.50
        res_50 = evaluate_detector(gt_dict, data, iou_thresh=0.50)
        report += f"| {det} | >= 0.50 | {res_50['TP']} | {res_50['FP']} | {res_50['FN']} | {res_50['Precision']:.4f} | {res_50['Recall']:.4f} | {res_50['F1']:.4f} | {res_50['mIoU']:.4f} | {total_gt} | {total_pred} |\n"
        
        # Evaluate at IoU 0.75
        res_75 = evaluate_detector(gt_dict, data, iou_thresh=0.75)
        report += f"| {det} | >= 0.75 | {res_75['TP']} | {res_75['FP']} | {res_75['FN']} | {res_75['Precision']:.4f} | {res_75['Recall']:.4f} | {res_75['F1']:.4f} | {res_75['mIoU']:.4f} | {total_gt} | {total_pred} |\n"
        
    report_path = r"E:\ANPR\benchmark\reports\state_wise_olx_detector_results.md"
    with open(report_path, "w") as f:
        f.write(report)
        
    print("Evaluated detectors and wrote to", report_path)

if __name__ == "__main__":
    main()
