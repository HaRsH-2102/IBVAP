import cv2
import csv
import os
import copy

CSV_PATH = r"e:\ANPR\benchmark\manual_validation\ground_truth.csv"
IMG_DIR = r"e:\ANPR\benchmark\manual_validation\images"

def load_annotations():
    annotations = {}
    if not os.path.exists(CSV_PATH):
        return annotations
    
    with open(CSV_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            img = row["image_path"]
            if img not in annotations:
                annotations[img] = []
            
            # Skip empty initial template rows
            if not row["ground_truth_plate"] and not row["x1"]:
                continue
                
            annotations[img].append(row)
    return annotations

def save_annotations(all_images, annotations):
    fieldnames = ['image_path', 'plate_id', 'ground_truth_plate', 'x1', 'y1', 'x2', 'y2', 'condition', 'notes']
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for img in all_images:
            if img in annotations and len(annotations[img]) > 0:
                for idx, ann in enumerate(annotations[img]):
                    ann["plate_id"] = idx + 1
                    writer.writerow(ann)
            else:
                # Write empty row so we don't lose the image from the list
                writer.writerow({
                    "image_path": img,
                    "plate_id": "1",
                    "ground_truth_plate": "",
                    "x1": "", "y1": "", "x2": "", "y2": "",
                    "condition": "", "notes": ""
                })
    print(f"[*] Progress saved to {CSV_PATH}")

drawing = False
ix, iy = -1, -1
bx, by = -1, -1
current_image = None
img_clean = None
need_input = False

def draw_rect(event, x, y, flags, param):
    global ix, iy, bx, by, drawing, current_image, img_clean, need_input
    
    if need_input:
        return
        
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
        bx, by = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            bx, by = x, y
            temp = img_clean.copy()
            cv2.rectangle(temp, (ix, iy), (bx, by), (0, 255, 0), 2)
            cv2.imshow("Annotation Tool", temp)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        bx, by = x, y
        cv2.rectangle(img_clean, (ix, iy), (bx, by), (0, 255, 0), 2)
        cv2.imshow("Annotation Tool", img_clean)
        if abs(bx - ix) > 10 and abs(by - iy) > 10:
            need_input = True

def prompt_terminal():
    print("\n--- NEW PLATE ---")
    plate_text = input("Enter ground truth plate text: ").strip()
    print("Conditions: CLEAR, SMALL, BLUR, NIGHT, GLARE, ANGLE, OCCLUSION, TWO_LINE, MOTORCYCLE, CAR, TRUCK, BUS, OTHER")
    condition = input("Enter condition (or leave empty): ").strip().upper()
    notes = input("Enter notes (or leave empty): ").strip()
    return plate_text, condition, notes

def main():
    global current_image, img_clean, need_input, ix, iy, bx, by
    
    images = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
    if not images:
        print("No images found.")
        return
        
    annotations = load_annotations()
    
    # Read from CSV if available to maintain order, else sort
    csv_images = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["image_path"] not in csv_images:
                    csv_images.append(row["image_path"])
    
    for img in images:
        if img not in csv_images:
            csv_images.append(img)
            
    images = csv_images
    idx = 0
    
    cv2.namedWindow("Annotation Tool")
    cv2.setMouseCallback("Annotation Tool", draw_rect)
    
    while True:
        img_name = images[idx]
        img_path = os.path.join(IMG_DIR, img_name)
        img_clean = cv2.imread(img_path)
        
        if img_clean is None:
            print(f"Failed to load {img_path}")
            idx = (idx + 1) % len(images)
            continue
            
        # Draw existing annotations
        display_img = img_clean.copy()
        if img_name in annotations:
            for ann in annotations[img_name]:
                if ann.get("ground_truth_plate") == "NO_PLATE":
                    cv2.putText(display_img, "NO_PLATE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                elif ann.get("ground_truth_plate") == "UNREADABLE":
                    cv2.putText(display_img, "UNREADABLE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                elif ann.get("x1") and ann.get("y1"):
                    try:
                        x1, y1, x2, y2 = int(ann["x1"]), int(ann["y1"]), int(ann["x2"]), int(ann["y2"])
                        cv2.rectangle(display_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        cv2.putText(display_img, ann.get("ground_truth_plate", ""), (x1, max(y1-10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    except ValueError:
                        pass
        
        # Display overlay text
        cv2.putText(display_img, f"Image {idx+1} / {len(images)} : {img_name}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("Annotation Tool", display_img)
        img_clean = display_img.copy()
        
        key = cv2.waitKey(50) & 0xFF
        
        if need_input:
            # We have a bounding box ready to be saved
            x1, y1 = min(ix, bx), min(iy, by)
            x2, y2 = max(ix, bx), max(iy, by)
            text, cond, notes = prompt_terminal()
            
            if img_name not in annotations:
                annotations[img_name] = []
                
            annotations[img_name].append({
                "image_path": img_name,
                "ground_truth_plate": text,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "condition": cond,
                "notes": notes
            })
            save_annotations(images, annotations)
            need_input = False
            continue
            
        if key == ord('q'):
            save_annotations(images, annotations)
            print("Exiting.")
            break
        elif key == ord('n') or key == 83: # 'n' or Right Arrow
            idx = (idx + 1) % len(images)
        elif key == ord('p') or key == 81: # 'p' or Left Arrow
            idx = (idx - 1) % len(images)
        elif key == ord('d'):
            annotations[img_name] = []
            save_annotations(images, annotations)
            print("Cleared annotations for this image.")
        elif key == ord('u'):
            annotations[img_name] = [{
                "image_path": img_name,
                "ground_truth_plate": "UNREADABLE",
                "x1": "", "y1": "", "x2": "", "y2": "",
                "condition": "", "notes": "Marked unreadable"
            }]
            save_annotations(images, annotations)
            print("Marked as UNREADABLE.")
        elif key == ord('m'):
            annotations[img_name] = [{
                "image_path": img_name,
                "ground_truth_plate": "NO_PLATE",
                "x1": "", "y1": "", "x2": "", "y2": "",
                "condition": "", "notes": "No plate present"
            }]
            save_annotations(images, annotations)
            print("Marked as NO_PLATE.")

if __name__ == "__main__":
    main()
