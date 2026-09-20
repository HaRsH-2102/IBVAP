import os
import cv2
import numpy as np
import logging

from app.domain.system_config import SystemConfiguration

logger = logging.getLogger("IBVAP.EvidenceStorage")

class EvidenceStorage:
    """
    Manages filesystem layout and operations for Evidence artifacts (images).
    """
    def __init__(self, config: SystemConfiguration):
        self.base_path = config.storage_base_path
        self.image_format = config.evidence_image_format.lower()
        self.image_quality = config.evidence_image_quality
        
    def _ensure_dir(self, directory: str):
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
    def _get_evidence_dir(self, camera_id: str, date_str: str, evidence_id: str) -> str:
        # e.g., storage/evidence/cam_01/2026-08-25/ev_uuid4/
        return os.path.join(self.base_path, "evidence", camera_id, date_str, evidence_id)

    def save_evidence_artifacts(self, camera_id: str, date_str: str, evidence_id: str, 
                                original_frame: np.ndarray, annotated_frame: np.ndarray) -> tuple[str, str]:
        """
        Saves both original and annotated frames to disk.
        Returns the paths (original_path, annotated_path).
        """
        dir_path = self._get_evidence_dir(camera_id, date_str, evidence_id)
        self._ensure_dir(dir_path)
        
        orig_path = os.path.join(dir_path, f"{evidence_id}_original.{self.image_format}")
        annot_path = os.path.join(dir_path, f"{evidence_id}_annotated.{self.image_format}")
        
        # Determine encoding parameters
        encode_params = []
        if self.image_format in ("jpeg", "jpg"):
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.image_quality]
        elif self.image_format == "png":
            # 0-9 for compression
            encode_params = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
            
        success_orig = cv2.imwrite(orig_path, original_frame, encode_params)
        success_annot = cv2.imwrite(annot_path, annotated_frame, encode_params)
        
        if not success_orig or not success_annot:
            logger.error(f"Failed to write image artifacts to {dir_path}")
            raise IOError("Failed to write image artifacts to filesystem.")
            
        return orig_path, annot_path

    def verify_artifacts_exist(self, original_path: str, annotated_path: str) -> bool:
        """Check if physical files exist on disk for reconciliation."""
        if not original_path or not annotated_path:
            return False
        return os.path.exists(original_path) and os.path.exists(annotated_path)
