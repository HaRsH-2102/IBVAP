"""
IBVAP ANPR Engine
=================
Milestone 9: Handles license plate detection, OCR, validation, and temporal aggregation.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple

import numpy as np

from app.config import settings
from app.domain.track import Track, TrackState
from app.domain.anpr import ANPREvent
from app.perception.plate_detector import PlateDetector
from app.perception.ocr_engine import OCREngine
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.evidence_storage import EvidenceStorage
from app.domain.system_config import SystemConfiguration
import json
import cv2
import os

class ANPREngine:
    def __init__(self):
        self._logger = logging.getLogger("ibvap.anpr_engine")
        
        self.enabled = settings.anpr_enabled
        if not self.enabled:
            self._logger.info("ANPR is disabled in configuration.")
            return
            
        # Initialize Plate Detector (FCOS)
        self.plate_detector = PlateDetector(
            confidence_threshold=settings.anpr_detector_confidence,
            device=settings.detector_device
        )
        
        # Initialize OCR Engine
        self.ocr_engine = OCREngine()
        
        # Temporal Consensus Memory
        # Format: Track ID -> list of dicts {"text", "norm_text", "conf", "plate_conf", "p_box", "v_box"}
        self._consensus_memory: Dict[str, List[Dict[str, Any]]] = {}
        self._solved_tracks: Dict[str, bool] = {}
        
        # Frame counters to limit plate detection intervals
        self._track_frame_counters: Dict[str, int] = {}
        self.plate_detection_interval = 3  # Configurable: run plate detection every 3 frames per track

    def process(self, camera_id: str, frame_data: np.ndarray, tracks: List[Track], timestamp: datetime) -> List[ANPREvent]:
        if not self.enabled or frame_data is None:
            return []
            
        anpr_events = []
        
        # Clean up memory for removed tracks
        active_track_ids = {t.track_id for t in tracks}
        stale_ids = set(self._consensus_memory.keys()) - active_track_ids
        for tid in stale_ids:
            del self._consensus_memory[tid]
            if tid in self._solved_tracks:
                del self._solved_tracks[tid]
            if tid in self._track_frame_counters:
                del self._track_frame_counters[tid]

        for track in tracks:
            # 1. State Gate
            if track.state != TrackState.ACTIVE:
                continue
                
            # If we already have a high-confidence consensus for this track, skip it.
            if self._solved_tracks.get(track.track_id):
                continue
                
            # 2. Vehicle Class Gate (Only Cars, Trucks, Buses, Motorcycles)
            valid_classes = ["car", "truck", "bus", "motorcycle"]
            if track.object_class.name.lower() not in valid_classes:
                continue
                
            # Rate limit plate detection per track
            self._track_frame_counters[track.track_id] = self._track_frame_counters.get(track.track_id, 0) + 1
            if self._track_frame_counters[track.track_id] % self.plate_detection_interval != 0:
                continue

            # 3. Vehicle Size Quality Gate
            left = int(track.bounding_box.left)
            top = int(track.bounding_box.top)
            right = int(track.bounding_box.right)
            bottom = int(track.bounding_box.bottom)
            width = right - left
            if width < settings.anpr_min_vehicle_width:
                continue
                
            # Crop Vehicle
            # Add padding just in case plate is on the edge
            H, W, _ = frame_data.shape
            pad = 10
            c_left = max(0, left - pad)
            c_top = max(0, top - pad)
            c_right = min(W, right + pad)
            c_bottom = min(H, bottom + pad)
            
            vehicle_crop = frame_data[c_top:c_bottom, c_left:c_right]
            if vehicle_crop.size == 0:
                continue

            # 4. Plate Detection (on crop)
            plate_detections = self.plate_detector.detect_in_crop(vehicle_crop)
            if not plate_detections:
                continue
                
            # Pick highest confidence plate
            # (px1, py1, px2, py2, p_conf) relative to vehicle_crop
            best_plate = max(plate_detections, key=lambda x: x[4])
            px1, py1, px2, py2, p_conf = best_plate
            
            # Map plate bounding box back to original frame coordinates
            abs_px1 = c_left + int(px1)
            abs_py1 = c_top + int(py1)
            abs_px2 = c_left + int(px2)
            abs_py2 = c_top + int(py2)
            
            p_width = abs_px2 - abs_px1
            if p_width < settings.anpr_min_plate_width:
                continue
                
            # Crop Plate from original frame (or vehicle crop)
            plate_crop = vehicle_crop[int(py1):int(py2), int(px1):int(px2)]
            if plate_crop.size == 0:
                continue
                
            # 5. OCR & Normalization
            result = self.ocr_engine.read_plate(plate_crop)
            if not result:
                continue
                
            norm_text, ocr_conf = result
            
            # 6. Format Plausibility
            plausibility = self.ocr_engine.evaluate_plausibility(norm_text)
            if plausibility < 0.3:
                continue  # Too implausible
                
            # 7. Temporal Aggregation
            if track.track_id not in self._consensus_memory:
                self._consensus_memory[track.track_id] = []
                
            memory = self._consensus_memory[track.track_id]
            memory.append({
                "norm_text": norm_text,
                "ocr_conf": ocr_conf,
                "plate_conf": p_conf,
                "plausibility": plausibility,
                "p_box": {"x1": abs_px1, "y1": abs_py1, "x2": abs_px2, "y2": abs_py2},
                "v_box": {"x1": c_left, "y1": c_top, "x2": c_right, "y2": c_bottom},
                "plate_crop": plate_crop, # Storing briefly for evidence
                "vehicle_crop": vehicle_crop
            })
            
            # Check Consensus
            event = self._evaluate_consensus(track, memory, camera_id, timestamp, frame_data)
            if event:
                anpr_events.append(event)
                
        return anpr_events
        
    def _evaluate_consensus(self, track: Track, memory: List[Dict[str, Any]], camera_id: str, timestamp: datetime, full_frame: np.ndarray) -> ANPREvent | None:
        """
        Evaluates if the history of reads for a track has reached the consensus threshold.
        """
        # Count identical normalized reads
        counts = {}
        for obs in memory:
            t = obs["norm_text"]
            counts[t] = counts.get(t, 0) + 1
            
        best_text = max(counts, key=counts.get)
        max_count = counts[best_text]
        
        if max_count >= settings.anpr_consensus_threshold:
            self._logger.info(f"ANPR Consensus Reached: {best_text} for Track {track.track_id} (count={max_count})")
            self._solved_tracks[track.track_id] = True
            
            # Extract the best observation for this text (highest combined confidence + plausibility)
            best_obs = max([obs for obs in memory if obs["norm_text"] == best_text], 
                           key=lambda x: x["ocr_conf"] * x["plausibility"])
                           
            # 8. Evidence Generation
            # We save the crops locally to storage
            evidence_id = f"anpr_ev_{uuid.uuid4().hex[:8]}"
            date_str = timestamp.strftime("%Y-%m-%d")
            config = SystemConfiguration.from_settings(settings)
            storage = EvidenceStorage(config)
            
            # Save artifacts
            dir_path = storage._get_evidence_dir(camera_id, date_str, evidence_id)
            storage._ensure_dir(dir_path)
            
            v_crop_path = os.path.join(dir_path, f"{evidence_id}_vehicle.jpg")
            p_crop_path = os.path.join(dir_path, f"{evidence_id}_plate.jpg")
            ff_path = os.path.join(dir_path, f"{evidence_id}_full.jpg")
            
            cv2.imwrite(v_crop_path, best_obs["vehicle_crop"])
            cv2.imwrite(p_crop_path, best_obs["plate_crop"])
            cv2.imwrite(ff_path, full_frame)
            
            # Clear large images from memory
            for obs in memory:
                obs.pop("plate_crop", None)
                obs.pop("vehicle_crop", None)
            
            event = ANPREvent(
                event_id=f"anpr-{uuid.uuid4().hex[:8]}",
                camera_id=camera_id,
                track_id=track.track_id,
                plate_text=best_text,
                raw_ocr_text=best_text, # Same as normalized text here
                plate_detection_confidence=float(best_obs["plate_conf"]),
                confidence=float(best_obs["ocr_conf"]),
                timestamp=timestamp,
                vehicle_class=track.object_class.name.lower(),
                plate_bounding_box=best_obs["p_box"],
                vehicle_bounding_box=best_obs["v_box"],
                evidence={
                    "plausibility": best_obs["plausibility"],
                    "observation_count": len(memory),
                    "consensus_count": max_count,
                    "evidence_id": evidence_id,
                    "artifacts": {
                        "full_frame": ff_path,
                        "vehicle_crop": v_crop_path,
                        "plate_crop": p_crop_path
                    }
                }
            )
            
            self._persist_event(event)
            return event
            
        return None
        
    def _persist_event(self, event: ANPREvent):
        try:
            db = SQLiteDatabase()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Combine extra fields into evidence JSON
            evidence_json = dict(event.evidence)
            evidence_json["raw_ocr_text"] = event.raw_ocr_text
            evidence_json["plate_detection_confidence"] = event.plate_detection_confidence
            evidence_json["plate_bounding_box"] = event.plate_bounding_box
            evidence_json["vehicle_bounding_box"] = event.vehicle_bounding_box
            
            cursor.execute(
                """
                INSERT INTO anpr_reads 
                (event_id, camera_id, track_id, plate_text, confidence, vehicle_class, timestamp, evidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.camera_id,
                    event.track_id,
                    event.plate_text,
                    event.confidence,
                    event.vehicle_class,
                    event.timestamp.isoformat(),
                    json.dumps(evidence_json),
                    datetime.utcnow().isoformat()
                )
            )
            conn.commit()
        except Exception as e:
            self._logger.error(f"Failed to persist ANPR read: {e}")
