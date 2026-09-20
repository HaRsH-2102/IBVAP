"""
Diagnostic ANPR Script
"""

import sys
import os
import cv2
import json

from app.perception.plate_detector import PlateDetector
from app.anpr.engines.adapters import EasyOCRAdapter

IMAGE_PATHS = [
    r"E:\SIH 2026\IBVAP\backend\results\evidence\INTRUSION\d8176e61-616e-4e68-a5bb-cf99428bcb52_crop.jpg",
    r"E:\SIH 2026\IBVAP\backend\results\evidence\LOITERING\b3db09cd-a962-46c6-b68d-4a9781926745_crop.jpg"
]

def main():
    print("==================================================")
    print(" ANPR DIAGNOSTIC RUNNER ")
    print("==================================================\n")
    
    # Init Models
    fcos = PlateDetector()
    easyocr_adapter = EasyOCRAdapter()
    
    os.makedirs("benchmark_results/fcos_debug", exist_ok=True)
    
    for path in IMAGE_PATHS:
        print(f"\n--- Processing Image: {os.path.basename(path)} ---")
        img = cv2.imread(path)
        if img is None:
            print("FAILED TO LOAD IMAGE")
            continue
            
        h, w, c = img.shape
        print(f"Vehicle Crop Dimensions: {w}x{h}")
        
        event_id = os.path.basename(path).replace("_crop.jpg", "")
        evt_debug_dir = f"benchmark_results/fcos_debug/{event_id}"
        os.makedirs(evt_debug_dir, exist_ok=True)
        
        # FCOS Diagnostic
        print("\n--- FCOS Candidate Inspection (Raw) ---")
        # Run FCOS at threshold 0.05 to see all raw candidates
        fcos.conf = 0.05
        raw_candidates = fcos.detect_in_crop(img)
        
        # Sort candidates by confidence
        raw_candidates.sort(key=lambda x: x[4], reverse=True)
        
        if raw_candidates:
            print(f"Highest candidate confidence: {raw_candidates[0][4]:.4f}")
            if len(raw_candidates) > 1:
                print(f"Second highest confidence: {raw_candidates[1][4]:.4f}")
        else:
            print("Highest candidate confidence: NO CANDIDATES FOUND EVEN AT 0.05")
            
        # Threshold evaluation
        print("\n--- FCOS Threshold Evaluation ---")
        thresholds = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70]
        
        for t in thresholds:
            fcos.conf = t
            candidates = fcos.detect_in_crop(img)
            if candidates:
                print(f"Threshold {t:.2f} -> {len(candidates)} candidates")
                best = max(candidates, key=lambda x: x[4])
                
                # Save diagnostic image
                debug_img = img.copy()
                x1, y1, x2, y2, conf = best
                cv2.rectangle(debug_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(debug_img, f"Conf: {conf:.2f} (Thresh: {t:.2f})", (int(x1), max(int(y1) - 10, 0)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imwrite(f"{evt_debug_dir}/threshold_{t:.2f}.jpg", debug_img)
            else:
                print(f"Threshold {t:.2f} -> 0 candidates")
                
        # EasyOCR Diagnostic
        print("\n--- EasyOCR Adapter Output ---")
        res = easyocr_adapter.process_crop(img, event_id, "cam1", "trk1")
        print(f"Raw OCR Text: {res['raw_text']}")
        print(f"Normalized Text: {res['normalized_text']}")
        print(f"Confidence: {res['ocr_confidence']:.4f}")
        print(f"BBOX: {res['plate_bbox']}")
        if res['plate_bbox']:
            bw = res['plate_bbox'][2] - res['plate_bbox'][0]
            bh = res['plate_bbox'][3] - res['plate_bbox'][1]
            print(f"Bbox Size: {bw}x{bh} (Image is {w}x{h})")
            if bw > w * 0.8 and bh > h * 0.8:
                print("WARNING: TEXT DETECTED — PLATE LOCALIZATION NOT PROVEN (Bbox is almost the entire image)")
            elif bw > w * 0.5 or bh > h * 0.5:
                print("TEXT DETECTED — PLATE LOCALIZATION WEAK (Bbox is very large)")
            else:
                print("Text localized to a smaller region.")

if __name__ == "__main__":
    main()
