"""
IBVAP ANPR — Engine Discovery Script
====================================

Dynamically inspects the environment to determine which ANPR engines
can actually run on this machine (Test B requirement).
"""

import sys
import importlib
import logging
from app.anpr.engines.adapters import FCOSAdapter, EasyOCRAdapter, PaddleOCRAdapter

def check_package(pkg_name: str) -> bool:
    try:
        importlib.import_module(pkg_name)
        return True
    except ImportError:
        return False

def discover_engines():
    print("=======================================")
    print(" IBVAP ANPR Engine Discovery           ")
    print("=======================================\n")
    
    print(f"Python version: {sys.version.split(' ')[0]}")
    
    # Check PyTorch and CUDA
    torch_avail = check_package('torch')
    if torch_avail:
        import torch
        print(f"PyTorch installed: True (v{torch.__version__})")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
    else:
        print("PyTorch installed: False")
        
    print("\n--- Candidate OCR Packages ---")
    ocr_pkgs = {
        "easyocr": "EasyOCR",
        "paddleocr": "PaddleOCR",
        "rapidocr_onnxruntime": "RapidOCR",
        "pytesseract": "Tesseract"
    }
    
    for pkg, name in ocr_pkgs.items():
        avail = check_package(pkg)
        print(f"{name:<12}: {'AVAILABLE' if avail else 'UNAVAILABLE (missing '+pkg+')'}")
        
    print("\n--- Adapter Availability Test ---")
    adapters = [
        FCOSAdapter(),
        EasyOCRAdapter(),
        PaddleOCRAdapter()
    ]
    
    available_adapters = []
    for a in adapters:
        if a.is_available:
            available_adapters.append(a.name)
            print(f"Adapter '{a.name}': AVAILABLE")
        else:
            print(f"Adapter '{a.name}': UNAVAILABLE")
            
    print("\n=======================================")
    print(f"Total Available Engines: {len(available_adapters)}")
    print("=======================================")
    
if __name__ == "__main__":
    discover_engines()
