import torch
from ultralytics import YOLO
import easyocr
import cv2
import sys

image_path = r"e:\ANPR\google_images\0073797c-a755-4972-b76b-8ef2b31d44ab___new_IMG_20160315_071740.jpg.jpeg"
img = cv2.imread(image_path)
if img is None:
    print("Could not load image")
    sys.exit(1)

models = [
    r"e:\ANPR\ANPR-Indian-License-Plate-Detection\license.pt",
    r"e:\ANPR\ANPR-Indian-License-Plate-Detection\ANPR2.pt",
    r"e:\ANPR\Auto-Num-Plate-Recognition\best.pt"
]

print("--- Testing YOLO Detectors ---")
for mp in models:
    try:
        model = YOLO(mp)
        results = model(img, verbose=False)
        print(f"Loaded {mp.split(chr(92))[-1]} successfully. Found {len(results[0].boxes)} boxes.")
    except Exception as e:
        print(f"Failed {mp}: {e}")

print("--- Testing EasyOCR ---")
try:
    reader = easyocr.Reader(['en'], gpu=True)
    res = reader.readtext(img)
    print(f"EasyOCR loaded and read {len(res)} text blocks.")
except Exception as e:
    print(f"EasyOCR failed: {e}")
