import os
import glob
import xml.etree.ElementTree as ET
import csv
import hashlib

def get_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    dataset_dir = r"E:\ANPR\video_images"
    out_dir = r"E:\ANPR\benchmark\ground_truth"
    os.makedirs(out_dir, exist_ok=True)
    
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    all_files = glob.glob(os.path.join(dataset_dir, "**", "*"), recursive=True)
    images = [f for f in all_files if os.path.isfile(f) and os.path.splitext(f)[1].lower() in valid_exts]
    
    seen_hashes = set()
    unique_images = []
    
    for img_path in images:
        h = get_hash(img_path)
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_images.append(img_path)
            
    print(f"Physical images: {len(images)}")
    print(f"Unique images: {len(unique_images)}")
    print(f"Duplicates skipped: {len(images) - len(unique_images)}")
    
    gt_mapping = []
    matched = 0
    missing_gt = 0
    
    for img_path in unique_images:
        base, ext = os.path.splitext(img_path)
        xml_path = base + ".xml"
        
        if os.path.exists(xml_path):
            matched += 1
            
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                size = root.find("size")
                width = int(size.find("width").text) if size is not None else 0
                height = int(size.find("height").text) if size is not None else 0
                
                plates = []
                for obj in root.findall("object"):
                    name = obj.find("name").text
                    bndbox = obj.find("bndbox")
                    xmin = int(bndbox.find("xmin").text)
                    ymin = int(bndbox.find("ymin").text)
                    xmax = int(bndbox.find("xmax").text)
                    ymax = int(bndbox.find("ymax").text)
                    plates.append(f"{name}|{xmin},{ymin},{xmax},{ymax}")
                    
                gt_mapping.append({
                    "source_image": img_path,
                    "gt_image": xml_path,
                    "filename": os.path.basename(img_path),
                    "width": width,
                    "height": height,
                    "gt_type": "PascalVOC_BBox_Text",
                    "status": "OK",
                    "plates": ";".join(plates)
                })
            except Exception as e:
                print(f"Error parsing {xml_path}: {e}")
                gt_mapping.append({
                    "source_image": img_path,
                    "gt_image": xml_path,
                    "filename": os.path.basename(img_path),
                    "width": 0,
                    "height": 0,
                    "gt_type": "PascalVOC_Error",
                    "status": f"Parse_Error: {str(e)}",
                    "plates": ""
                })
                
        else:
            missing_gt += 1
            gt_mapping.append({
                "source_image": img_path,
                "gt_image": "",
                "filename": os.path.basename(img_path),
                "width": 0,
                "height": 0,
                "gt_type": "None",
                "status": "Missing_GT",
                "plates": ""
            })
            
    print(f"Matched images: {matched}")
    print(f"Missing GT: {missing_gt}")
    
    csv_path = os.path.join(out_dir, "video_images_gt_mapping.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source_image", "gt_image", "filename", "width", "height", "gt_type", "status", "plates"])
        writer.writeheader()
        writer.writerows(gt_mapping)
        
    print(f"Mapping saved to {csv_path}")

if __name__ == "__main__":
    main()
