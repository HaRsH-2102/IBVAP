import os
import sys
import json
import subprocess
import tempfile
from typing import List, Dict
import numpy as np
import cv2
from .base import BaseOCR

class PaddleOCRAdapter(BaseOCR):
    def __init__(self, python_exe: str, script_path: str, is_awiros: bool = False):
        """
        python_exe: path to python executable in the paddle environment
        script_path: path to the isolated paddle script
        """
        self.python_exe = python_exe
        self.script_path = script_path
        self.is_awiros = is_awiros

    def load_model(self, model_path: str = None):
        pass # Model is loaded in the subprocess

    def recognize(self, image: np.ndarray) -> List[Dict]:
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = os.path.join(tmpdir, "temp.jpg")
            out_json = os.path.join(tmpdir, "out.json")
            cv2.imwrite(img_path, image)

            cmd = [
                self.python_exe, 
                self.script_path,
                "--image_path", img_path,
                "--output_json", out_json
            ]

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print("PaddleOCR failed:", res.stderr)
                return []

            if os.path.exists(out_json):
                with open(out_json, "r") as f:
                    data = json.load(f)
                return data
            return []
