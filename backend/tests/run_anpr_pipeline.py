import os
import sys
import time
import argparse
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.opencv_stream import FileStreamManager
from app.ingestion.metrics import StreamMetrics
from app.ingestion.frame_pipeline import CameraPipeline
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker
from app.anpr.anpr_engine import ANPREngine
from app.event.pipeline import M6EventPipeline
from app.event.rule_engine import RuleEngine
from app.domain.rule import Rule
from app.domain.severity import SeverityLevel

def main():
    parser = argparse.ArgumentParser(description="M9 ANPR Pipeline Integration Test")
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--model", type=str, default="rtdetr-l.pt")
    parser.add_argument("--no-show", action="store_true")
    args = parser.parse_args()

    print("\n============================================================")
    print("Starting M9 Full Pipeline Validation with ANPR")
    print(f"Video: {args.video}")
    print(f"Main Model: {args.model}")
    print("Plate Model: Indian_LPR FCOS (best_od.pth)")
    print("============================================================\n")

    camera_id = "test_cam_1"
    metrics = StreamMetrics()
    stream_manager = FileStreamManager(camera_id, args.video)
    pipeline = CameraPipeline(stream_manager, metrics, playback_mode="max_throughput")
    
    # Init M3, M4, M9
    detector = YOLODetector(model_path=args.model, confidence_threshold=0.65, inference_size=1280)
    tracker = ByteTrackTracker(camera_id=camera_id)
    anpr_engine = ANPREngine()
    
    # M6EventPipeline is removed for now, as ANPREngine handles DB and Evidence.
    
    pipeline.start()
    print("Waiting for capture thread to warm up...")
    time.sleep(2)

    frames_processed = 0
    plate_consensus_map = {} # Track ID -> plate text
    total_plate_detections = 0
    total_ocr_reads = 0
    start_time = time.time()
    
    try:
        while pipeline.is_running:
            frame = pipeline.get_next_frame(timeout=1.0)
            if not frame:
                if pipeline.is_running:
                    continue
                break
                
            current_time = frame.timestamp
            
            # M3 -> M4
            detections = detector.detect(frame)
            tracks = tracker.update(detections, frame)
            
            # M9 ANPR
            anpr_events = anpr_engine.process(camera_id, frame.data, tracks, current_time)
            
            for evt in anpr_events:
                plate_consensus_map[evt.track_id] = evt
                
            frames_processed += 1
            
            if not args.no_show:
                vis = frame.data.copy()
                for track in tracks:
                    if track.state.name != "ACTIVE":
                        continue
                    l = int(track.bounding_box.left)
                    t = int(track.bounding_box.top)
                    r = int(track.bounding_box.right)
                    b = int(track.bounding_box.bottom)
                    cv2.rectangle(vis, (l, t), (r, b), (0, 255, 0), 2)
                    
                    label = f"ID:{track.track_id}"
                    if track.track_id in plate_consensus_map:
                        evt = plate_consensus_map[track.track_id]
                        label += f" | {evt.plate_text} (conf: {evt.confidence:.2f})"
                        cv2.rectangle(vis, (l, t-35), (l+300, t), (0, 0, 0), -1)
                        cv2.putText(vis, label, (l, t-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    else:
                        cv2.putText(vis, label, (l, t-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        
                cv2.imshow("M9 ANPR Pipeline", vis)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        pipeline.stop()
        if not args.no_show:
            cv2.destroyAllWindows()
            
        elapsed = time.time() - start_time
        fps = frames_processed / elapsed if elapsed > 0 else 0
            
        print(f"\nProcessed {frames_processed} frames in {elapsed:.2f}s ({fps:.2f} FPS).")
        print(f"Total ANPR Plates Captured: {len(plate_consensus_map)}")
        for tid, evt in plate_consensus_map.items():
            print(f"  Track ID: {tid} -> Plate: {evt.plate_text} | OCR Conf: {evt.confidence:.2f} | Det Conf: {evt.plate_detection_confidence:.2f}")

if __name__ == "__main__":
    main()
