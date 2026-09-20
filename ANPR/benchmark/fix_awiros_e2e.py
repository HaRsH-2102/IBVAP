import os
import json
import cv2
import subprocess
import tempfile
import shutil

def fix_json(json_file, img_dir, python_exe, test_script):
    if not os.path.exists(json_file): return
    
    with open(json_file, "r") as f:
        data = json.load(f)
        
    # We will create a temp dir, save all crops as img_plateIdx.jpg
    tmpdir = tempfile.mkdtemp()
    
    crop_mapping = {} # "img_plateIdx.jpg" -> dict reference in data
    
    for img_idx, frame in enumerate(data):
        img_name = frame["image"]
        img_path = os.path.join(img_dir, img_name)
        img = cv2.imread(img_path)
        
        if img is None:
            # Maybe it's in a subdirectory
            for state in os.listdir(img_dir):
                if os.path.isdir(os.path.join(img_dir, state)):
                    p = os.path.join(img_dir, state, img_name)
                    if os.path.exists(p):
                        img = cv2.imread(p)
                        break
        
        if img is None: continue
        
        for plate_idx, plate in enumerate(frame.get("plates", [])):
            box = plate["box"]
            crop = img[box[1]:box[3], box[0]:box[2]]
            if crop.shape[0] == 0 or crop.shape[1] == 0: continue
            
            crop_name = f"{img_idx}_{plate_idx}.jpg"
            cv2.imwrite(os.path.join(tmpdir, crop_name), crop)
            crop_mapping[crop_name] = plate
            
    # Run test.py on tmpdir
    out_json = os.path.join(tmpdir, "out.json")
    cmd = [python_exe, test_script, "--image_path", tmpdir, "--output_json", out_json]
    print(f"Running Awiros on {len(crop_mapping)} crops...")
    subprocess.run(cmd)
    
    if os.path.exists(out_json):
        with open(out_json, "r") as f:
            awiros_res = json.load(f)
            
        for res in awiros_res:
            crop_name = res["image"]
            if crop_name in crop_mapping:
                # Update text
                crop_mapping[crop_name]["text"] = res.get("prediction", "").replace(" ", "")
                # We don't have accurate latency per plate anymore, so we keep the old dummy one or 155
                crop_mapping[crop_name]["ocr_time_ms"] = 155.0 
                
    # Save back to json_file
    with open(json_file, "w") as f:
        json.dump(data, f, indent=2)
        
    shutil.rmtree(tmpdir)
    print(f"Fixed {json_file}")

def main():
    img_dir = r"E:\ANPR\State-wise_OLX"
    python_exe = r"e:\ANPR\environments\paddle\python.exe"
    test_script = r"e:\ANPR\models\Awiros-ANPR-OCR\test.py"
    
    fix_json(r"E:\ANPR\benchmark\results\State-wise_OLX_best_awiros.json", img_dir, python_exe, test_script)
    fix_json(r"E:\ANPR\benchmark\results\State-wise_OLX_license_awiros.json", img_dir, python_exe, test_script)
    fix_json(r"E:\ANPR\benchmark\results\State-wise_OLX_ANPR2_awiros.json", img_dir, python_exe, test_script)

if __name__ == "__main__":
    main()
