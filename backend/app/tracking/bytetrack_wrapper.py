"""
IBVAP — ByteTrack Wrapper
=========================
A concrete implementation of the BaseTracker using Ultralytics' ByteTrack.

This file acts as a bridge between the IBVAP domain models (Detection, Track)
and the internal `BYTETracker` logic of `ultralytics`. It ensures that tracking
is completely isolated from the YOLO detector, preserving the clean architectural
boundary required by Milestone 4.
"""

from types import SimpleNamespace

import numpy as np
from ultralytics.trackers.byte_tracker import BYTETracker

from app.domain.detection import Detection, BoundingBox
from app.domain.track import Track, TrackPoint, TrackState
from app.ingestion.frame_pipeline import Frame
from app.tracking.tracker_interface import BaseTracker


class DummyResults:
    """
    Mock object to adapt our `Detection[]` list into the tensor format
    expected by `ultralytics.trackers.byte_tracker.BYTETracker._split_detections`.
    """

    def __init__(self, detections: list[Detection]):
        self.detections = detections
        
        confs = []
        clss = []
        xywhs = []
        
        self.CLASS_MAP = {
            "person": 0,
            "car": 1,
            "motorcycle": 2,
            "bus": 3,
            "truck": 4,
            "bicycle": 2 # Map bicycle to motorcycle if not in enum
        }
        
        for d in detections:
            confs.append(d.confidence)
            clss.append(self.CLASS_MAP.get(d.class_name.lower(), 1))  # Map to actual class ID
            
            x1, y1, x2, y2 = d.bbox_xyxy
            w = x2 - x1
            h = y2 - y1
            cx = x1 + w / 2.0
            cy = y1 + h / 2.0
            xywhs.append([cx, cy, w, h])
            
        # ByteTracker internals use these arrays
        self.conf = np.array(confs, dtype=np.float32) if confs else np.empty(0, dtype=np.float32)
        self.cls = np.array(clss, dtype=np.float32) if clss else np.empty(0, dtype=np.float32)
        self.xywh = np.array(xywhs, dtype=np.float32) if xywhs else np.empty((0, 4), dtype=np.float32)
        
    def __len__(self) -> int:
        return len(self.detections)
        
    def __getitem__(self, idx) -> 'DummyResults':
        # When BYTETracker does boolean indexing (e.g. results[remain_inds])
        if isinstance(idx, np.ndarray) and idx.dtype == bool:
            subset = [self.detections[i] for i, mask in enumerate(idx) if mask]
            return DummyResults(subset)
        raise NotImplementedError("DummyResults only supports boolean mask indexing.")


class ByteTrackTracker(BaseTracker):
    """
    Implementation of the IBVAP BaseTracker using ByteTrack.
    """

    def __init__(self, camera_id: str, track_buffer: int = 30, match_thresh: float = 0.8):
        """
        Initialize the ByteTrack instance.
        
        Args:
            camera_id: Unique identifier for the camera source.
            track_buffer: Frames to keep a track alive without detections before removing.
            match_thresh: IOU threshold for matching.
        """
        self.camera_id = camera_id
        self.track_buffer = track_buffer
        
        # We supply the configuration namespace expected by ultralytics BYTETracker
        self.args = SimpleNamespace(
            track_high_thresh=0.5,
            track_low_thresh=0.1,
            new_track_thresh=0.6,
            track_buffer=track_buffer,
            match_thresh=match_thresh,
            fuse_score=True,     # Whether to fuse confidence scores into distances
            gsi=False,           # Generalized Smoothing Interpolation (False by default)
            mot20=False          # MOT20 dataset format conventions (False by default)
        )
        
        self.tracker = BYTETracker(self.args)
        
        # Keep our own dictionary of canonical Track models
        # Dict[track_id, Track]
        self.active_tracks: dict[int, Track] = {}
        
        # Maximum number of trajectory points to keep per track to avoid memory leaks
        self.max_history = 300

    def update(self, detections: list[Detection], frame: Frame) -> list[Track]:
        """Update tracker state and return canonical Track models."""
        
        # 1. Adapt Detections to DummyResults
        dummy_results = DummyResults(detections)
        
        # 2. Update ByteTrack (internally advances kalman filters and frame_id)
        # We pass a None image since ByteTrack doesn't require pixels, only boxes.
        self.tracker.update(dummy_results, img=None)
        
        current_tracks = []
        
        # 3. Synchronize `tracker.tracked_stracks` (ACTIVE)
        for strack in self.tracker.tracked_stracks:
            if not strack.is_activated:
                continue
                
            track = self._sync_strack(strack, frame, TrackState.ACTIVE)
            current_tracks.append(track)
            
        # 4. Synchronize `tracker.lost_stracks` (LOST)
        for strack in self.tracker.lost_stracks:
            track = self._sync_strack(strack, frame, TrackState.LOST)
            current_tracks.append(track)
            
        # 5. Clean up `tracker.removed_stracks` (REMOVED)
        # We don't return removed tracks, but we need to delete them from our dictionary
        for strack in self.tracker.removed_stracks:
            if strack.track_id in self.active_tracks:
                self.active_tracks[strack.track_id].state = TrackState.REMOVED
                del self.active_tracks[strack.track_id]
                
        return current_tracks
        
    def _sync_strack(self, strack, frame: Frame, target_state: TrackState) -> Track:
        """Helper to convert/update an STrack into a canonical IBVAP Track."""
        
        track_id = strack.track_id
        
        # strack.tlwh returns [top-left x, top-left y, width, height]
        tl_x, tl_y, w, h = strack.tlwh
        bbox = BoundingBox(
            left=float(tl_x),
            top=float(tl_y),
            right=float(tl_x + w),
            bottom=float(tl_y + h)
        )
        
        point = TrackPoint(
            timestamp=frame.timestamp,
            bounding_box=bbox,
            frame_id=frame.frame_id
        )
        
        if track_id not in self.active_tracks:
            from app.domain.detection import ObjectClass
            
            REV_CLASS_MAP = {
                0: ObjectClass.PERSON,
                1: ObjectClass.CAR,
                2: ObjectClass.MOTORCYCLE,
                3: ObjectClass.BUS,
                4: ObjectClass.TRUCK
            }
            track_cls_id = int(getattr(strack, "cls", 1))
            obj_class = REV_CLASS_MAP.get(track_cls_id, ObjectClass.CAR)
            
            new_track = Track(
                track_id=f"{self.camera_id}-{track_id}",
                camera_id=self.camera_id,
                object_class=obj_class,
                bounding_box=bbox,
                first_seen=frame.timestamp,
                last_seen=frame.timestamp,
                trajectory=[point],
                state=target_state
            )
            self.active_tracks[track_id] = new_track
        else:
            # Update existing track
            existing = self.active_tracks[track_id]
            existing.bounding_box = bbox
            existing.last_seen = frame.timestamp
            existing.state = target_state
            
            # Append trajectory (only if ACTIVE, or maybe we append predicted for LOST)
            existing.trajectory.append(point)
            
            # Prune trajectory history
            if len(existing.trajectory) > self.max_history:
                existing.trajectory = existing.trajectory[-self.max_history:]
                
        return self.active_tracks[track_id]
