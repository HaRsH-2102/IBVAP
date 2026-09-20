import os
import cv2
import json
import time
import psutil
import torch
import uuid
from datetime import datetime

# Adjust sys path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker
from app.anpr.anpr_engine import ANPREngine
from app.domain.frame import Frame
from app.infrastructure.database import SQLiteDatabase
from app.config import settings

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def get_db_row_count():
    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM anpr_reads")
    return cursor.fetchone()[0]

def verify_fcos_checkpoint():
    print("=== FCOS Checkpoint Verification ===")
    ckpt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Indian_LPR-main", "weights", "best_od.pth"))
    
    print(f"Absolute Checkpoint Path: {ckpt_path}")
    print("Loading checkpoint...")
    try:
        if os.path.exists(ckpt_path):
            ckpt = torch.load(ckpt_path, map_location='cpu')
            print(f"Loading Success: YES")
            if isinstance(ckpt, dict):
                print(f"Keys in checkpoint: {list(ckpt.keys())}")
            else:
                print(f"Model type: {type(ckpt)}")
            print("Checkpoint is verified at runtime.")
        else:
            print("Loading Success: NO (File not found)")
    except Exception as e:
        print(f"Loading Success: NO ({e})")
    print("====================================\n")

def run_video(video_path, output_dir, camera_id="cam_test"):
    print(f"--- Processing {video_path} ---")
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        return None

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"Resolution: {width}x{height}, FPS: {fps:.2f}, Frames: {total_frames}, Duration: {duration:.2f}s")

    ensure_dir(output_dir)
    annotated_path = os.path.join(output_dir, "annotated_output.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(annotated_path, fourcc, int(fps) if fps > 0 else 30, (width, height))

    # Initialize modules
    detector = YOLODetector(model_path="rtdetr-l.pt", confidence_threshold=0.65)
    tracker = ByteTrackTracker(camera_id=camera_id)
    anpr = ANPREngine()
    
    metrics = {
        "video": video_path,
        "resolution": f"{width}x{height}",
        "source_fps": fps,
        "frame_count": total_frames,
        "duration_sec": duration,
        "processed_frames": 0,
        "raw_detections": 0,
        "rejected_detections": 0,
        "accepted_detections": 0,
        "vehicle_detections": 0,
        "plate_detections": 0,
        "ocr_observations": 0,
        "stable_plates": 0,
        "final_events": 0,
        "start_time": time.time(),
        "inference_times": [],
        "peak_vram_mb": 0
    }

    temporal_consensus = []
    generated_events = []
    active_observations = {}

    db_before = get_db_row_count()

    while True:
        ret, frame_img = cap.read()
        if not ret:
            break
            
        metrics["processed_frames"] += 1
        
        frame = Frame(
            frame_id=f"f_{metrics['processed_frames']}",
            camera_id=camera_id,
            timestamp=datetime.utcnow(),
            width=width,
            height=height,
            data=frame_img.copy()
        )

        t0 = time.time()
        # RT-DETR
        detections = detector.detect(frame)
        t1 = time.time()
        metrics["inference_times"].append(t1 - t0)

        metrics["accepted_detections"] += len(detections)
        vehicles = [d for d in detections if d.class_name in ["car", "bus", "truck", "motorcycle"]]
        metrics["vehicle_detections"] += len(vehicles)

        # ByteTrack
        tracks = tracker.update(detections, frame)

        # ANPREngine
        events = anpr.process(camera_id, frame.data, tracks, frame.timestamp)
        
        # Extract temporal consensus traces
        for tid, mem in anpr._consensus_memory.items():
            if tid not in active_observations:
                active_observations[tid] = []
            
            while len(active_observations[tid]) < len(mem):
                idx = len(active_observations[tid])
                obs = mem[idx]
                active_observations[tid].append({
                    "text": obs["norm_text"],
                    "confidence": float(obs["ocr_conf"]),
                    "plate_conf": float(obs["plate_conf"]),
                    "timestamp": frame.timestamp.isoformat()
                })
                metrics["plate_detections"] += 1
                metrics["ocr_observations"] += 1

        for ev in events:
            metrics["final_events"] += 1
            metrics["stable_plates"] += 1
            generated_events.append({
                "event_id": ev.event_id,
                "camera_id": ev.camera_id,
                "track_id": ev.track_id,
                "plate_text": ev.plate_text,
                "raw_ocr": ev.raw_ocr_text,
                "confidence": ev.confidence,
                "plate_detection_confidence": ev.plate_detection_confidence,
                "vehicle_class": ev.vehicle_class,
                "timestamp": ev.timestamp.isoformat(),
                "evidence_id": ev.evidence.get("evidence_id")
            })
            if ev.track_id in active_observations:
                temporal_consensus.append({
                    "camera_id": ev.camera_id,
                    "track_id": ev.track_id,
                    "observations": active_observations[ev.track_id],
                    "final_consensus": ev.plate_text
                })

        # Draw annotations
        for track in tracks:
            x1, y1, x2, y2 = track.bounding_box.left, track.bounding_box.top, track.bounding_box.right, track.bounding_box.bottom
            cv2.rectangle(frame_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame_img, f"{track.object_class.name} #{track.track_id}", (int(x1), int(y1)-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        for ev in events:
            pbox = ev.plate_bounding_box
            cv2.rectangle(frame_img, (int(pbox["x1"]), int(pbox["y1"])), (int(pbox["x2"]), int(pbox["y2"])), (0, 0, 255), 2)
            cv2.putText(frame_img, f"PLATE: {ev.plate_text}", (int(pbox["x1"]), int(pbox["y1"])-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        out.write(frame_img)

        if torch.cuda.is_available():
            vram = torch.cuda.max_memory_allocated() / (1024*1024)
            if vram > metrics["peak_vram_mb"]:
                metrics["peak_vram_mb"] = vram

    cap.release()
    out.release()
    
    end_time = time.time()
    metrics["total_time"] = end_time - metrics["start_time"]
    metrics["processing_fps"] = metrics["processed_frames"] / metrics["total_time"] if metrics["total_time"] > 0 else 0
    metrics["avg_inference_ms"] = (sum(metrics["inference_times"]) / len(metrics["inference_times"]) * 1000) if metrics["inference_times"] else 0
    
    db_after = get_db_row_count()
    metrics["db_rows_created"] = db_after - db_before

    # Save metadata
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=4)
        
    with open(os.path.join(output_dir, "temporal_consensus.json"), "w") as f:
        json.dump(temporal_consensus, f, indent=4)
        
    with open(os.path.join(output_dir, "anpr_events.json"), "w") as f:
        json.dump(generated_events, f, indent=4)

    print(f"Finished {video_path}. Generated {metrics['final_events']} events.")
    return metrics

def main():
    verify_fcos_checkpoint()
    
    videos = [
        "tests/assets/videoplayback.mp4",
        "test_video.mp4",
        "test_clip.mp4"
    ]
    
    base_out = os.path.abspath(os.path.join(os.path.dirname(__file__), "results", "anpr_phase10_validation"))
    ensure_dir(base_out)
    
    all_metrics = {}
    
    for v in videos:
        v_path = os.path.abspath(v)
        v_name = os.path.splitext(os.path.basename(v))[0]
        v_out = os.path.join(base_out, v_name)
        
        m = run_video(v_path, v_out, camera_id=f"cam_{v_name}")
        if m:
            all_metrics[v_name] = m

if __name__ == "__main__":
    main()
