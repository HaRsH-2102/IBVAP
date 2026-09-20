import sys
import json
import time
import os
import cv2
import numpy as np

# Ensure PaddleOCR is available
sys.path.insert(0, r"E:\ANPR\models\Awiros-ANPR-OCR")
sys.path.insert(0, r"E:\ANPR\PaddleOCR")

import paddle
from ppocr.modeling.architectures import build_model
from ppocr.postprocess import build_post_process
import copy

MODEL_CONFIG = {
    "Architecture": {
        "model_type": "rec",
        "algorithm": "SVTR_HGNet",
        "Transform": None,
        "Backbone": {"name": "PPHGNetV2_B4", "text_rec": True},
        "Head": {
            "name": "MultiHead",
            "out_channels_list": {
                "CTCLabelDecode": 64,
                "NRTRLabelDecode": 67,
            },
            "head_list": [
                {
                    "CTCHead": {
                        "Neck": {
                            "name": "svtr",
                            "dims": 120,
                            "depth": 2,
                            "hidden_dims": 120,
                            "kernel_size": [1, 3],
                            "use_guide": True,
                        },
                        "Head": {"fc_decay": 1e-05},
                    }
                },
                {"NRTRHead": {"nrtr_dim": 384, "max_text_length": 25}},
            ],
        },
    },
}

def load_safetensors_to_paddle(paddle_mod, weight_path: str):
    from safetensors.numpy import load_file
    np_state = load_file(weight_path)
    return {k: paddle_mod.to_tensor(v) for k, v in np_state.items()}

def resize_for_rec(img_bgr, target_shape):
    _, h, w = target_shape
    img_h, img_w = img_bgr.shape[:2]
    ratio = h / img_h
    new_w = min(int(img_w * ratio), w)
    resized = cv2.resize(img_bgr, (new_w, h))
    if new_w < w:
        padded = np.zeros((h, w, 3), dtype=np.uint8)
        padded[:, :new_w, :] = resized
        resized = padded
    return resized

def preprocess(img_bgr, target_shape):
    img = resize_for_rec(img_bgr, target_shape)
    img = img.astype(np.float32) / 255.0
    img = (img - 0.5) / 0.5
    return img.transpose((2, 0, 1))

def main():
    crop_dir = sys.argv[1]
    out_json = sys.argv[2]
    
    paddle.set_device("gpu" if paddle.is_compiled_with_cuda() else "cpu")
    
    dict_path = r"E:\ANPR\models\Awiros-ANPR-OCR\en_dict.txt"
    weights_path = r"E:\ANPR\models\Awiros-ANPR-OCR\model.safetensors"
    
    post_process = build_post_process({
        "name": "CTCLabelDecode",
        "character_dict_path": dict_path,
        "use_space_char": True,
    })
    
    config = copy.deepcopy(MODEL_CONFIG)
    model = build_model(config["Architecture"])
    model.eval()
    
    state_dict = load_safetensors_to_paddle(paddle, weights_path)
    model.set_state_dict(state_dict)
    
    results = {}
    crops = [f for f in os.listdir(crop_dir) if f.endswith(".jpg")]
    
    for c in crops:
        img_path = os.path.join(crop_dir, c)
        img_bgr = cv2.imread(img_path)
        if img_bgr is None: continue
        
        tensor = paddle.to_tensor(
            np.expand_dims(preprocess(img_bgr, [3, 48, 320]), axis=0)
        )
        
        start_time = time.perf_counter()
        with paddle.no_grad():
            preds = model(tensor)
            
        if isinstance(preds, dict):
            pred_tensor = preds.get("ctc", next(iter(preds.values())))
        elif isinstance(preds, (list, tuple)):
            pred_tensor = preds[0]
        else:
            pred_tensor = preds
            
        post_result = post_process(pred_tensor.numpy())
        ocr_time_ms = (time.perf_counter() - start_time) * 1000.0
        
        if isinstance(post_result, (list, tuple)) and len(post_result) > 0:
            text, confidence = post_result[0]
        else:
            text, confidence = "", 0.0
            
        text = text.strip()
        results[c] = {
            "text": text,
            "confidence": float(confidence),
            "ocr_time_ms": ocr_time_ms
        }
        
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
