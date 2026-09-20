import sys
import subprocess
import logging

# Suppress verbose paddle logging
logging.getLogger("ppocr").setLevel(logging.ERROR)

print("--- Testing PaddleOCR (Standard) ---")
try:
    from paddleocr import PaddleOCR
    import cv2
    image_path = r"e:\ANPR\google_images\0073797c-a755-4972-b76b-8ef2b31d44ab___new_IMG_20160315_071740.jpg.jpeg"
    img = cv2.imread(image_path)
    ocr = PaddleOCR(use_angle_cls=True, lang='en')
    result = ocr.ocr(img, cls=True)
    print(f"PaddleOCR (Standard) read {len(result[0]) if result and result[0] else 0} text blocks.")
except Exception as e:
    print(f"PaddleOCR (Standard) failed: {e}")

print("--- Testing Awiros-ANPR-OCR ---")
try:
    awiros_test = r"e:\ANPR\models\Awiros-ANPR-OCR\test.py"
    awiros_img = r"e:\ANPR\google_images\0073797c-a755-4972-b76b-8ef2b31d44ab___new_IMG_20160315_071740.jpg.jpeg"
    cmd = ["python", awiros_test, "--image_path", awiros_img]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("Awiros output:", res.stdout)
    if res.returncode != 0:
        print("Awiros error:", res.stderr)
except Exception as e:
    print(f"Awiros-ANPR-OCR failed: {e}")
