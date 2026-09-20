import torch
import time
from app.perception.yolo_detector import YOLODetector
import numpy as np

def verify():
    print("====================================")
    print("CUDA VERIFICATION")
    print("====================================")
    print(f"PyTorch Version: {torch.__version__}")
    is_available = torch.cuda.is_available()
    print(f"CUDA Available:  {is_available}")
    
    if is_available:
        print(f"CUDA Version:    {torch.version.cuda}")
        print(f"Device Name:     {torch.cuda.get_device_name(0)}")
    else:
        print("ERROR: CUDA IS NOT AVAILABLE!")
        return

    print("\n====================================")
    print("YOLO INFERENCE SMOKE TEST")
    print("====================================")
    
    try:
        # Load YOLOv8s with device="auto" (which should pick CUDA)
        detector = YOLODetector(
            model_path="yolov8s.pt",
            confidence_threshold=0.25,
            inference_size=1280,
            device="auto"
        )
        print(f"Model:           yolov8s.pt")
        print(f"Device:          {detector.device}")
        
        from app.domain.frame import Frame
        from datetime import datetime, timezone
        dummy_data = np.zeros((1080, 1920, 3), dtype=np.uint8)
        dummy_frame = Frame(frame_id="f-1", camera_id="cam-1", timestamp=datetime.now(timezone.utc), data=dummy_data)
        
        # Warmup
        detector.detect(dummy_frame)
        
        # Timed inference
        start = time.perf_counter()
        detector.detect(dummy_frame)
        end = time.perf_counter()
        
        latency = (end - start) * 1000
        print(f"Inference size:  1280")
        print(f"Confidence:      0.25")
        print(f"Inference lat.:  {latency:.2f} ms")
        
        if str(detector.device) != "cuda:0" and str(detector.device) != "cuda":
            print("ERROR: Inference did not run on CUDA!")
        else:
            print("SUCCESS: Inference ran on CUDA.")
            
    except Exception as e:
        print(f"ERROR during YOLO inference: {e}")

if __name__ == "__main__":
    verify()
