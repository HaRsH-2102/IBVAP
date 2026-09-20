import os
import sqlite3
import json
import shutil
import math

base_dir = r"E:\SIH 2026\IBVAP\backend"
evidence_root = os.path.join(base_dir, "results", "evidence")
manual_dir = os.path.join(evidence_root, "MANUAL_INSPECTION")
db_path = os.path.join(base_dir, "m6_events.db")
md_path = os.path.join(evidence_root, "EVIDENCE_MANUAL_INSPECTION.md")
readme_path = os.path.join(manual_dir, "README.txt")

os.makedirs(manual_dir, exist_ok=True)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get recent evidence that actually has crops (i.e. not deleted)
cur.execute("SELECT * FROM evidence_packages WHERE crop_path IS NOT NULL ORDER BY created_at DESC LIMIT 100")
rows = cur.fetchall()

# 1. Filter out deleted or non-existent files
valid_evidence = []
for r in rows:
    crop_path = os.path.join(base_dir, r['crop_path'].lstrip('/'))
    # The DB path might be an API path or absolute. Let's check how it's stored.
    # From earlier script, it was an absolute or relative path from backend.
    if r['crop_path'].startswith(r'E:\SIH'):
        crop_path = r['crop_path']
        full_path = r['full_frame_path']
    elif r['crop_path'].startswith('/api/v1'):
        # Just use results/evidence/...
        event_id = r['security_event_id']
        event_type = r['event_type']
        crop_path = os.path.join(evidence_root, event_type, f"{event_id}_crop.jpg")
        full_path = os.path.join(evidence_root, event_type, f"{event_id}_full.jpg")
    else:
        crop_path = os.path.join(base_dir, r['crop_path'])
        full_path = os.path.join(base_dir, r['full_frame_path'])

    if os.path.exists(crop_path) and os.path.exists(full_path):
        # We need bbox to determine edge cases
        bbox = json.loads(r['bbox']) if r['bbox'] else {"x1":0, "y1":0, "x2":0, "y2":0}
        valid_evidence.append({
            "event_id": r['security_event_id'],
            "event_type": r['event_type'],
            "camera_id": r['camera_id'],
            "track_id": r['track_id'],
            "frame_id": r['frame_id'],
            "timestamp": r['timestamp'],
            "object_class": r['object_class'],
            "bbox": bbox,
            "crop_path": crop_path,
            "full_path": full_path
        })

# Select first 20 for markdown
first_20 = valid_evidence[:20]

# Write EVIDENCE_MANUAL_INSPECTION.md
with open(md_path, "w", encoding="utf-8") as f:
    f.write("# EVIDENCE MANUAL INSPECTION INDEX\n\n")
    f.write("| # | Event ID | Event Type | Track ID | Frame ID | Timestamp | Crop | Full Scene |\n")
    f.write("|---|---|---|---|---|---|---|---|\n")
    for i, ev in enumerate(first_20, 1):
        f.write(f"| {i} | {ev['event_id']} | {ev['event_type']} | {ev['track_id']} | {ev['frame_id']} | {ev['timestamp']} | `{ev['crop_path']}` | `{ev['full_path']}` |\n")

# Select 10 representative packages
# - normal person event
# - vehicle event if available
# - different Track IDs
# - different timestamps
# - object near an image edge if available
# - different event types if available

selected = []
def add_sample(ev):
    if len(selected) < 10 and ev not in selected:
        selected.append(ev)

# Heuristics
has_person = False
has_vehicle = False
has_edge = False
has_loitering = False
has_intrusion = False

for ev in valid_evidence:
    bb = ev['bbox']
    is_edge = (bb.get('x1', 0) < 50) or (bb.get('y1', 0) < 50) or (bb.get('x2', 0) > 3790) or (bb.get('y2', 0) > 2110)
    is_vehicle = ev['object_class'] in ['car', 'truck', 'bus', 'motorcycle']
    is_person = ev['object_class'] == 'person'
    
    if is_edge and not has_edge:
        add_sample(ev)
        has_edge = True
    elif is_vehicle and not has_vehicle:
        add_sample(ev)
        has_vehicle = True
    elif is_person and not has_person:
        add_sample(ev)
        has_person = True
    elif ev['event_type'] == 'LOITERING' and not has_loitering:
        add_sample(ev)
        has_loitering = True
    elif ev['event_type'] == 'INTRUSION' and not has_intrusion:
        add_sample(ev)
        has_intrusion = True

# Fill up to 10
for ev in valid_evidence:
    if len(selected) >= 10:
        break
    if ev not in selected:
        add_sample(ev)

# Copy files
for ev in selected:
    c_dest = os.path.join(manual_dir, f"{ev['event_id']}_crop.jpg")
    f_dest = os.path.join(manual_dir, f"{ev['event_id']}_full.jpg")
    shutil.copy(ev['crop_path'], c_dest)
    shutil.copy(ev['full_path'], f_dest)

# Write README.txt
readme_text = """MANUAL INSPECTION GUIDE

This folder contains the generated evidence files representing a subset of recent Security Events.
For each event, two images are provided:

1. {event_id}_crop.jpg (Primary Evidence)
   - This is the 25% margin crop of the specific person or vehicle that triggered the event.
   - It contains an embedded black metadata panel containing the Track ID, timestamp, and rule description.

2. {event_id}_full.jpg (Full-Scene Context)
   - This is the pristine, full-resolution 4K source frame from the exact moment the event occurred.
   - It features a red bounding box strictly highlighting the triggering object.

INSPECTION CHECKLIST:
- Visual BBox Alignment: Open the _crop.jpg and verify the red bounding box correctly wraps the object.
- Crop Correctness: Verify the crop margin gives adequate context but stays tightly focused.
- Edge Cropping: Verify edge cases (if object was near screen edge) did not cause crashes or malformed borders.
- Metadata Correctness: Check the metadata panel at the bottom of the crop image against the actual object visually.
- Exact Match: Ensure the _full.jpg corresponds precisely to the scene shown in the _crop.jpg.

Selected Event Samples:
"""
for ev in selected:
    readme_text += f"- Event ID: {ev['event_id']} | Type: {ev['event_type']} | Class: {ev['object_class']} | Track: {ev['track_id']} | Frame: {ev['frame_id']} | Timestamp: {ev['timestamp']}\n"

with open(readme_path, "w", encoding="utf-8") as f:
    f.write(readme_text)

# Save selected output for the agent to report
with open(os.path.join(base_dir, "selected_samples.json"), "w") as f:
    json.dump([e['event_id'] for e in selected], f)

print(f"Index created at {md_path}")
print(f"Manual dir created at {manual_dir}")
print(f"Copied {len(selected)} samples")
