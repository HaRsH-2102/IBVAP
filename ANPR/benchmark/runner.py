import os
import sys
import json
import glob
import cv2
import time
from pathlib import Path
from tqdm import tqdm

from adapters.yolo_detector import YOLODetector
from adapters.easyocr_adapter import EasyOCRAdapter
from adapters.paddleocr_adapter import PaddleOCRAdapter

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ANPR Benchmark Runner")
    parser.add_argument("--detector", type=str, required=True, help="Path to detector model (e.g., license.pt)")
    parser.add_argument("--ocr", type=str, required=True, choices=["easyocr", "paddleocr", "awiros"], help="OCR Engine")
    parser.add_argument("--dataset", type=str, required=True, help="Path to dataset image directory")
    parser.add_argument("--output", type=str, required=True, help="Output JSON path")
    parser.add_argument("--paddle_env_python", type=str, default=r"e:\ANPR\environments\paddle\python.exe")
    parser.add_argument("--paddle_script", type=str, default=r"e:\ANPR\models\Awiros-ANPR-OCR\test.py")
    args = parser.parse_args()

    # Load Detector
    print(f"Loading Detector: {args.detector}")
    detector = YOLODetector(args.detector)

    # Load OCR
    print(f"Loading OCR: {args.ocr}")
    if args.ocr == "easyocr":
        ocr = EasyOCRAdapter()
    elif args.ocr == "paddleocr":
        ocr = PaddleOCRAdapter(args.paddle_env_python, args.paddle_script, is_awiros=False)
    elif args.ocr == "awiros":
        ocr = PaddleOCRAdapter(args.paddle_env_python, args.paddle_script, is_awiros=True)

    # Find images
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_paths = []
    for root, _, files in os.walk(args.dataset):
        for f in files:
            if Path(f).suffix.lower() in image_exts:
                image_paths.append(os.path.join(root, f))
    
    print(f"Found {len(image_paths)} images in {args.dataset}")

    results = []
    for img_path in tqdm(image_paths, desc="Processing images"):
        img = cv2.imread(img_path)
        if img is None:
            continue
        
        # Detect plates
        t0 = time.time()
        detections = detector.detect(img)
        det_time = time.time() - t0
        
        frame_result = {
            "image": os.path.basename(img_path),
            "det_time_ms": round(det_time * 1000, 2),
            "plates": []
        }

        for det in detections:
            x1, y1, x2, y2 = det['box']
            plate_crop = img[y1:y2, x1:x2]
            
            # Skip invalid crops
            if plate_crop.shape[0] == 0 or plate_crop.shape[1] == 0:
                continue

            # Run OCR on the crop
            t1 = time.time()
            ocr_res = ocr.recognize(plate_crop)
            ocr_time = time.time() - t1
            
            # Since OCR may return multiple blocks, combine them or take highest conf
            combined_text = ""
            if ocr_res:
                if isinstance(ocr_res, list):
                    # Combine texts
                    combined_text = " ".join([r.get('text', r.get('prediction', '')) for r in ocr_res])
                else:
                    combined_text = ocr_res.get('prediction', '')
            
            frame_result["plates"].append({
                "box": det['box'],
                "detector_conf": det['confidence'],
                "text": combined_text.replace(" ", ""),
                "ocr_time_ms": round(ocr_time * 1000, 2)
            })
        
        results.append(frame_result)

    # Save results
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Saved results to {args.output}")

if __name__ == "__main__":
    main()
