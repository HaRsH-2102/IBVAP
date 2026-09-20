import os
import json
import cv2
import argparse
from pathlib import Path
from tqdm import tqdm

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Path to result JSON")
    parser.add_argument("--dataset", required=True, help="Path to original dataset images")
    parser.add_argument("--output", required=True, help="Output directory for visualizations")
    args = parser.parse_args()

    with open(args.json, "r") as f:
        data = json.load(f)

    os.makedirs(args.output, exist_ok=True)

    for item in tqdm(data, desc="Visualizing"):
        img_name = item["image"]
        
        # find image in dataset
        img_path = None
        for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            p = os.path.join(args.dataset, img_name)
            if os.path.exists(p):
                img_path = p
                break
        
        if not img_path:
            # Fallback search
            for root, _, files in os.walk(args.dataset):
                if img_name in files:
                    img_path = os.path.join(root, img_name)
                    break
        
        if not img_path:
            continue

        img = cv2.imread(img_path)
        if img is None:
            continue

        for plate in item["plates"]:
            x1, y1, x2, y2 = plate["box"]
            text = plate.get("text", "")
            conf = plate.get("detector_conf", 0.0)

            # Draw box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw text
            label = f"{text} ({conf:.2f})"
            cv2.putText(img, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        out_path = os.path.join(args.output, img_name)
        cv2.imwrite(out_path, img)

if __name__ == "__main__":
    main()
