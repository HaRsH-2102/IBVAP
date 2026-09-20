import os
import glob
import json
import csv

def bb_intersection_over_union(boxA, boxB):
    # box: [x1, y1, x2, y2]
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

def calculate_accuracy(pred, gt):
    if not gt: return 0.0
    pred = pred.replace(" ", "").upper()
    gt = gt.replace(" ", "").upper()
    if pred == gt:
        return 1.0
    # Character accuracy
    matches = sum(1 for a, b in zip(pred, gt) if a == b)
    return matches / max(len(pred), len(gt))

def main():
    gt_csv = r"e:\ANPR\benchmark\manual_validation\ground_truth.csv"
    if not os.path.exists(gt_csv):
        print(f"Ground truth file not found: {gt_csv}")
        return
        
    gt_data = {}
    with open(gt_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gt_data[row["image_path"]] = row

    results_dir = r"e:\ANPR\benchmark\results"
    json_files = glob.glob(os.path.join(results_dir, "*.json"))
    
    report = "# ANPR End-to-End Audit Report\n\n"
    report += "This report evaluates Detector and OCR accuracy against the manual validation set.\n\n"
    report += "| Dataset | Detector | OCR | Precision | Recall | Avg IoU | OCR Exact Match | OCR Char Acc | End-to-End Match |\n"
    report += "|---|---|---|---|---|---|---|---|---|\n"

    for jf in json_files:
        name_parts = os.path.basename(jf).replace(".json", "").split("_")
        ocr_engine = name_parts[-1]
        detector = name_parts[-2]
        dataset = "_".join(name_parts[:-2])
        
        with open(jf, "r") as f:
            data = json.load(f)
            
        tp, fp, fn = 0, 0, 0
        total_iou = 0
        iou_count = 0
        
        exact_matches = 0
        total_char_acc = 0.0
        ocr_eval_count = 0
        
        e2e_matches = 0

        for img_res in data:
            img_name = img_res["image"]
            if img_name not in gt_data:
                continue
                
            gt = gt_data[img_name]
            has_gt = bool(gt.get("plate_bbox_x1"))
            
            if not has_gt:
                continue
                
            try:
                gt_box = [
                    int(gt["plate_bbox_x1"]),
                    int(gt["plate_bbox_y1"]),
                    int(gt["plate_bbox_x2"]),
                    int(gt["plate_bbox_y2"])
                ]
            except ValueError:
                continue # Missing/invalid box
                
            gt_text = gt.get("ground_truth_plate", "").strip()
            
            preds = img_res["plates"]
            if not preds:
                fn += 1
                continue
                
            # Find best matching box
            best_iou = 0
            best_pred = None
            for p in preds:
                iou = bb_intersection_over_union(p["box"], gt_box)
                if iou > best_iou:
                    best_iou = iou
                    best_pred = p
            
            if best_iou > 0.4:
                tp += 1
                total_iou += best_iou
                iou_count += 1
                fp += (len(preds) - 1)
                
                # Evaluate OCR
                pred_text = best_pred.get("text", "")
                if gt_text:
                    ocr_eval_count += 1
                    acc = calculate_accuracy(pred_text, gt_text)
                    total_char_acc += acc
                    if acc == 1.0:
                        exact_matches += 1
                        e2e_matches += 1
            else:
                fp += len(preds)
                fn += 1

        if (tp + fp) == 0:
            precision = 0.0
        else:
            precision = tp / (tp + fp)
            
        if (tp + fn) == 0:
            recall = 0.0
        else:
            recall = tp / (tp + fn)
            
        avg_iou = total_iou / iou_count if iou_count > 0 else 0.0
        
        if ocr_eval_count == 0:
            ocr_exact = 0.0
            ocr_char = 0.0
            e2e = 0.0
        else:
            ocr_exact = exact_matches / ocr_eval_count
            ocr_char = total_char_acc / ocr_eval_count
            e2e = e2e_matches / (tp + fn) # End-to-end includes missed detections
            
        report += f"| {dataset} | {detector} | {ocr_engine} | {precision:.2f} | {recall:.2f} | {avg_iou:.2f} | {ocr_exact:.2f} | {ocr_char:.2f} | {e2e:.2f} |\n"

    report_path = r"e:\ANPR\reports\audit_evaluate.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
        
    print(f"Audit evaluate report saved to {report_path}")

if __name__ == "__main__":
    main()
