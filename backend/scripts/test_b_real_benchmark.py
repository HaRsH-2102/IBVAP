"""
IBVAP ANPR — TEST B: Real ANPR Performance Benchmark
====================================================

Extracts REAL vehicle evidence from the IBVAP database and runs the 
available isolated ANPR engines to evaluate read rate and performance.
"""

import sys
import os
import json
import argparse
import asyncio
from datetime import datetime
from collections import defaultdict
import cv2

from app.infrastructure.database import SQLiteDatabase
from app.domain.security import SecurityEvent, EvidencePackage
from app.anpr.benchmark_architecture import is_anpr_eligible
from app.anpr.engines.adapters import FCOSAdapter, EasyOCRAdapter, PaddleOCRAdapter

def fetch_real_evidence_from_db():
    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Fetch all events and their evidence
    cursor.execute("""
        SELECT e.*, 
               s.event_type as sec_event_type, 'PROCESSED' as sec_status 
        FROM evidence_packages e
        JOIN security_events s ON e.security_event_id = s.event_id
    """)
    rows = cursor.fetchall()
    
    events = []
    evidences = []
    
    for r in rows:
        evt = SecurityEvent(
            event_id=r["security_event_id"],
            event_type=r["sec_event_type"],
            severity="HIGH", # mockup, doesn't matter for filter
            camera_id=r["camera_id"],
            track_id=r["track_id"],
            source_spatial_event_id="N/A",
            rule_id="N/A",
            timestamp=datetime.now(),
            status=r["sec_status"]
        )
        evd = EvidencePackage(
            evidence_id=r["evidence_id"],
            event_id=r["security_event_id"],
            camera_id=r["camera_id"],
            track_id=r["track_id"],
            frame_id=r["frame_id"],
            timestamp=datetime.now(),
            event_type=r["event_type"],
            object_class=r["object_class"],
            bbox=json.loads(r["bbox"]) if r["bbox"] else {},
            crop_path=r["crop_path"],
            full_frame_path=r["full_frame_path"],
            created_at=datetime.now(),
            expires_at=None,
            is_saved=bool(r["is_saved"]),
            saved_at=None
        )
        events.append(evt)
        evidences.append(evd)
        
    return events, evidences

def draw_debug_image(crop, anpr_res, output_path):
    if crop is None or not anpr_res["plate_detected"]:
        return
        
    debug_img = crop.copy()
    bbox = anpr_res["plate_bbox"]
    if bbox:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        text = f"{anpr_res['normalized_text']} ({anpr_res['ocr_confidence']:.2f})"
        cv2.putText(debug_img, text, (x1, max(y1 - 10, 0)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
    cv2.imwrite(output_path, debug_img)

async def run_benchmark(prepare_only=False):
    print("=======================================")
    print(" TEST B: REAL ANPR PERFORMANCE         ")
    print("=======================================\n")
    
    events, evidences = fetch_real_evidence_from_db()
    
    stats = {
        "Total Events": len(events),
        "Person Events": 0,
        "Vehicle Events": 0,
        "Eligible Events": 0,
        "Rejected Events": 0
    }
    
    eligible_pairs = []
    unique_tracks = set()
    
    for evt, evd in zip(events, evidences):
        if evd.object_class.lower() == "person":
            stats["Person Events"] += 1
        else:
            stats["Vehicle Events"] += 1
            
        if is_anpr_eligible(evt, evd):
            stats["Eligible Events"] += 1
            eligible_pairs.append((evt, evd))
            unique_tracks.add(evd.track_id)
        else:
            stats["Rejected Events"] += 1
            
    print("--- Event & Dataset Statistics ---")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print(f"Total unique tracks: {len(unique_tracks)}")
    
    # 1. Prepare Dataset mode
    if prepare_only:
        print("\n--- Generating Ground Truth Template ---")
        gt = []
        for evt, evd in eligible_pairs[:100]: # max 100 for manual
            gt.append({
                "image": evd.crop_path,
                "event_id": evt.event_id,
                "camera_id": evt.camera_id,
                "track_id": evt.track_id,
                "ground_truth_plate": "TODO",
                "plate_visible": True,
                "quality": "HIGH|LOW"
            })
            
        with open("ground_truth_template.json", "w") as f:
            json.dump(gt, f, indent=4)
        print(f"Saved {len(gt)} samples to ground_truth_template.json. Please manually annotate.")
        return
        
    print("\n--- Running Multi-Engine Benchmark ---")
    
    adapters = [FCOSAdapter(), EasyOCRAdapter()]
    active_adapters = [a for a in adapters if a.is_available]
    
    if not active_adapters:
        print("No ANPR engines available! Exiting.")
        return
        
    print(f"Executing with engines: {[a.name for a in active_adapters]}")
    
    os.makedirs("benchmark_results", exist_ok=True)
    
    # Check if ground truth exists
    gt_file = "ground_truth.json"
    ground_truth = {}
    if os.path.exists(gt_file):
        with open(gt_file, "r") as f:
            data = json.load(f)
            for item in data:
                ground_truth[item["event_id"]] = item["ground_truth_plate"]
        print(f"Loaded ground truth for {len(ground_truth)} events.")
    else:
        print("No ground_truth.json found. Exact accuracy will NOT be reported.")
        
    results = defaultdict(lambda: {"total": 0, "detected": 0, "read": 0, "total_time": 0, "exact_matches": 0})
    
    for evt, evd in eligible_pairs:
        crop = cv2.imread(evd.crop_path)
        if crop is None:
            continue
            
        evt_dir = f"benchmark_results/event_{evt.event_id}"
        os.makedirs(evt_dir, exist_ok=True)
        cv2.imwrite(f"{evt_dir}/vehicle.jpg", crop)
        
        gt_plate = ground_truth.get(evt.event_id)
        
        for adapter in active_adapters:
            res = adapter.process_crop(crop, evt.event_id, evd.camera_id, evd.track_id)
            
            # Metrics
            results[adapter.name]["total"] += 1
            results[adapter.name]["total_time"] += res["processing_time_ms"]
            if res["plate_detected"]:
                results[adapter.name]["detected"] += 1
                if res["normalized_text"]:
                    results[adapter.name]["read"] += 1
                    
            if gt_plate and gt_plate != "TODO":
                if res["normalized_text"] == gt_plate:
                    results[adapter.name]["exact_matches"] += 1
                    
            # Visual Debugging
            engine_dir = f"{evt_dir}/{adapter.name}"
            os.makedirs(engine_dir, exist_ok=True)
            draw_debug_image(crop, res, f"{engine_dir}/result.jpg")

    print("\n--- FINAL ACCEPTANCE REPORT ---")
    for name, r in results.items():
        if r["total"] == 0: continue
        print(f"\nEngine: {name}")
        print(f"Total Run: {r['total']}")
        print(f"Plate Detection Rate: {r['detected']/r['total']*100:.1f}%")
        print(f"OCR Read Rate: {r['read']/r['total']*100:.1f}%")
        print(f"Avg Processing Time: {r['total_time']/r['total']:.1f} ms")
        if ground_truth:
            print(f"Exact Plate Accuracy: {r['exact_matches']/r['total']*100:.1f}%")
            
    print("\nBenchmark completed. Visuals saved to benchmark_results/")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-dataset", action="store_true")
    args = parser.parse_args()
    
    asyncio.run(run_benchmark(prepare_only=args.prepare_dataset))
