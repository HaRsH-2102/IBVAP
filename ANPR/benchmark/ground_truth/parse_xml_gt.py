import os
import glob
import xml.etree.ElementTree as ET
import csv

def parse_xml(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        return {"error": f"Failed to parse XML: {str(e)}"}
    
    filename = root.find("filename")
    filename = filename.text if filename is not None else ""
    
    size = root.find("size")
    if size is not None:
        width = size.find("width")
        width = width.text if width is not None else ""
        height = size.find("height")
        height = height.text if height is not None else ""
    else:
        width, height = "", ""
        
    state = os.path.basename(os.path.dirname(xml_file))
    
    objects = []
    for obj in root.findall("object"):
        name = obj.find("name")
        name = name.text if name is not None else ""
        
        bndbox = obj.find("bndbox")
        if bndbox is not None:
            xmin = bndbox.find("xmin")
            xmin = xmin.text if xmin is not None else ""
            ymin = bndbox.find("ymin")
            ymin = ymin.text if ymin is not None else ""
            xmax = bndbox.find("xmax")
            xmax = xmax.text if xmax is not None else ""
            ymax = bndbox.find("ymax")
            ymax = ymax.text if ymax is not None else ""
        else:
            xmin, ymin, xmax, ymax = "", "", "", ""
            
        objects.append({
            "name": name,
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax
        })
        
    return {
        "filename": filename,
        "width": width,
        "height": height,
        "state": state,
        "objects": objects
    }

def main():
    base_dir = r"E:\ANPR\State-wise_OLX"
    output_csv = r"E:\ANPR\benchmark\ground_truth\state_wise_olx_gt.csv"
    report_md = r"E:\ANPR\benchmark\reports\state_wise_olx_ground_truth_report.md"
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    os.makedirs(os.path.dirname(report_md), exist_ok=True)
    
    xml_files = glob.glob(os.path.join(base_dir, "**", "*.xml"), recursive=True)
    
    total_xml = len(xml_files)
    valid_xml = 0
    invalid_xml = 0
    total_images_ref = 0
    total_gt_plates = 0
    images_multiple_plates = 0
    missing_images = 0
    invalid_bboxes = 0
    empty_labels = 0
    duplicates = 0
    state_distribution = {}
    
    seen_annotations = set()
    
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image_path", "plate_id", "ground_truth_plate", "x1", "y1", "x2", "y2", "image_width", "image_height", "state", "source_xml"])
        
        for xml_file in xml_files:
            res = parse_xml(xml_file)
            if "error" in res:
                invalid_xml += 1
                continue
                
            valid_xml += 1
            filename = res["filename"]
            # XML might just have "AN1.jpg", but it's in a state folder.
            # Easiest way to resolve is look in the same folder as the XML
            img_path = os.path.join(os.path.dirname(xml_file), filename)
            
            # If the filename in XML doesn't match the actual file name on disk, let's try the XML name but with .jpg
            if not os.path.exists(img_path):
                alt_filename = os.path.basename(xml_file).replace(".xml", ".jpg")
                alt_path = os.path.join(os.path.dirname(xml_file), alt_filename)
                if os.path.exists(alt_path):
                    img_path = alt_path
                    filename = alt_filename
                else:
                    alt_filename = os.path.basename(xml_file).replace(".xml", ".png")
                    alt_path = os.path.join(os.path.dirname(xml_file), alt_filename)
                    if os.path.exists(alt_path):
                        img_path = alt_path
                        filename = alt_filename
            
            if not os.path.exists(img_path):
                missing_images += 1
                continue
                
            total_images_ref += 1
            
            # Count plates
            plate_count = len(res["objects"])
            if plate_count > 1:
                images_multiple_plates += 1
                
            state = res["state"]
            state_distribution[state] = state_distribution.get(state, 0) + plate_count
            
            plate_id = 1
            for obj in res["objects"]:
                # Validation
                name = obj["name"].strip()
                if not name:
                    empty_labels += 1
                
                try:
                    x1, y1 = int(obj["xmin"]), int(obj["ymin"])
                    x2, y2 = int(obj["xmax"]), int(obj["ymax"])
                    w, h = int(res["width"]), int(res["height"])
                    
                    if not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
                        invalid_bboxes += 1
                        
                except ValueError:
                    invalid_bboxes += 1
                    x1, y1, x2, y2 = 0, 0, 0, 0
                    
                # Deduplication
                ann_tuple = (filename, name, x1, y1, x2, y2)
                if ann_tuple in seen_annotations:
                    duplicates += 1
                    continue
                seen_annotations.add(ann_tuple)
                
                rel_img_path = os.path.join(state, filename)
                rel_xml_path = os.path.join(state, os.path.basename(xml_file))
                
                writer.writerow([
                    rel_img_path,
                    plate_id,
                    name,
                    x1, y1, x2, y2,
                    res["width"], res["height"],
                    state,
                    rel_xml_path
                ])
                total_gt_plates += 1
                plate_id += 1

    report = f"""# State-wise_OLX Ground Truth Validation Report

## Summary
- **Total XML files discovered:** {total_xml}
- **Valid XML files parsed:** {valid_xml}
- **Invalid XML files:** {invalid_xml}
- **Total images referenced:** {total_images_ref}
- **Missing images:** {missing_images}

## Plate Annotations
- **Total GT plate instances:** {total_gt_plates}
- **Images with multiple plates:** {images_multiple_plates}
- **Invalid bounding boxes:** {invalid_bboxes}
- **Empty labels:** {empty_labels}
- **Duplicate annotations ignored:** {duplicates}

## Sample Verification (AN1.jpg)
"""
    # Verify AN1.jpg specifically
    an1_found = False
    with open(output_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "AN1.jpg" in row["image_path"]:
                an1_found = True
                report += f"- Image: {row['image_path']}\n"
                report += f"- Dimensions: {row['image_width']}x{row['image_height']}\n"
                report += f"- Ground truth plate: {row['ground_truth_plate']}\n"
                report += f"- BBox: x1={row['x1']}, y1={row['y1']}, x2={row['x2']}, y2={row['y2']}\n"
                break
                
    if not an1_found:
        report += "- **ERROR: AN1.jpg NOT FOUND IN DATASET!**\n"

    report += "\n## State Distribution\n"
    for state, count in sorted(state_distribution.items()):
        report += f"- {state}: {count} plates\n"

    with open(report_md, "w") as f:
        f.write(report)
        
    print(f"Parsed {total_gt_plates} plates from {total_xml} XML files.")

if __name__ == "__main__":
    main()
