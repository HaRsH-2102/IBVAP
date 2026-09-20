import os
import csv
import cv2

def main():
    gt_csv = r"E:\ANPR\benchmark\ground_truth\state_wise_olx_gt.csv"
    base_dir = r"E:\ANPR\State-wise_OLX"
    crop_dir = r"E:\ANPR\benchmark\results\state_wise_olx\gt_plate_crops"
    crop_csv_path = r"E:\ANPR\benchmark\results\state_wise_olx\gt_plate_crops\crop_mapping.csv"
    
    os.makedirs(crop_dir, exist_ok=True)
    
    with open(gt_csv, "r") as f:
        reader = list(csv.DictReader(f))
        
    crop_mapping = []
    
    for row in reader:
        img_path = os.path.join(base_dir, row["image_path"])
        if not os.path.exists(img_path):
            continue
            
        img = cv2.imread(img_path)
        if img is None:
            continue
            
        try:
            x1, y1 = int(row["x1"]), int(row["y1"])
            x2, y2 = int(row["x2"]), int(row["y2"])
        except ValueError:
            continue
            
        # Ensure bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
        
        crop = img[y1:y2, x1:x2]
        if crop.shape[0] == 0 or crop.shape[1] == 0:
            continue
            
        crop_filename = f"{os.path.basename(row['image_path']).replace('.jpg', '')}_p{row['plate_id']}.jpg"
        crop_path = os.path.join(crop_dir, crop_filename)
        
        cv2.imwrite(crop_path, crop)
        
        new_row = row.copy()
        new_row["crop_path"] = crop_filename
        crop_mapping.append(new_row)
        
    with open(crop_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["crop_path", "image_path", "plate_id", "ground_truth_plate", "x1", "y1", "x2", "y2", "image_width", "image_height", "state", "source_xml"])
        writer.writeheader()
        writer.writerows(crop_mapping)
        
    print(f"Created {len(crop_mapping)} ground-truth crops in {crop_dir}")

if __name__ == "__main__":
    main()
