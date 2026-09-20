import os
import logging
from dataclasses import dataclass
from typing import List
from app.infrastructure.database import SQLiteDatabase
from app.infrastructure.clip_repository import SQLiteClipRepository

logger = logging.getLogger("IBVAP.ArtifactReconciliation")

@dataclass
class ReconciliationResult:
    clip_id: str
    security_event_id: str
    status: str
    message: str

class ArtifactReconciliation:
    def __init__(self, db: SQLiteDatabase, storage_base_path: str):
        self.db = db
        self.repo = SQLiteClipRepository(self.db)
        self.storage_base_path = storage_base_path

    def reconcile(self) -> List[ReconciliationResult]:
        results = []
        
        # 1. Gather all files from filesystem
        filesystem_artifacts = set()
        evidence_dir = os.path.join(self.storage_base_path, "evidence")
        if os.path.exists(evidence_dir):
            for root, dirs, files in os.walk(evidence_dir):
                for f in files:
                    if f in ["incident_clip.mp4", "thumbnail.jpg"]:
                        filesystem_artifacts.add(os.path.join(root, f))
                        
        # 2. Reconcile DB against files
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT clip_id, security_event_id, clip_path, thumbnail_path FROM incident_clips")
        db_records = cursor.fetchall()
        
        matched_files = set()
        
        for row in db_records:
            clip_id = row["clip_id"]
            sec_event_id = row["security_event_id"]
            clip_path = row["clip_path"]
            thumb_path = row["thumbnail_path"]
            
            missing = []
            if clip_path:
                if os.path.exists(clip_path):
                    matched_files.add(clip_path)
                else:
                    missing.append("MP4")
            
            if thumb_path:
                if os.path.exists(thumb_path):
                    matched_files.add(thumb_path)
                else:
                    missing.append("Thumbnail")
                    
            if not missing:
                results.append(ReconciliationResult(clip_id, sec_event_id, "VALID", "All artifacts exist."))
            else:
                results.append(ReconciliationResult(clip_id, sec_event_id, "ARTIFACT_MISSING", f"Missing artifacts: {', '.join(missing)}"))
                
        # 3. Find Orphaned Files
        orphans = filesystem_artifacts - matched_files
        for orphan in orphans:
            results.append(ReconciliationResult(
                clip_id="UNKNOWN",
                security_event_id="UNKNOWN",
                status="ORPHANED_ARTIFACT",
                message=f"Orphaned file found: {orphan}"
            ))
            
        return results
