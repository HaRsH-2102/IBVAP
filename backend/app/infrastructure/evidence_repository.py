import json
import logging
from typing import List, Optional
import sqlite3
from datetime import datetime

from app.domain.evidence import EvidencePackage, EvidenceStatus, EvidenceQuality
from app.infrastructure.database import SQLiteDatabase

logger = logging.getLogger("IBVAP.EvidenceRepository")

class LocalEvidenceRepository:
    def __init__(self, database: SQLiteDatabase):
        self.db = database

    def create_evidence(self, package: EvidencePackage) -> bool:
        """
        Inserts a new EvidencePackage into the database.
        Returns True if successful. Raises IntegrityError if security_event_id is duplicate.
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            meta = dict(package.metadata)
            if package.failure_reason:
                meta["failure_reason"] = package.failure_reason
            metadata_str = json.dumps(meta)
            
            cursor.execute("""
                INSERT INTO evidence_packages (
                    evidence_id, security_event_id, alert_id, camera_id, track_id, 
                    event_type, timestamp, evidence_quality, status, 
                    original_frame_path, annotated_frame_reference, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                package.evidence_id,
                package.security_event_id,
                package.alert_id,
                package.camera_id,
                package.track_id,
                package.event_type,
                package.timestamp.isoformat(),
                package.evidence_quality.value if package.evidence_quality else None,
                package.status.value,
                package.original_frame_path,
                package.annotated_frame_reference,
                metadata_str,
                package.created_at.isoformat()
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            conn.rollback()
            # IDEMPOTENCY: We expect this if duplicate.
            logger.warning(f"Duplicate evidence for security_event_id={package.security_event_id}: {e}")
            raise e
        except Exception as e:
            conn.rollback()
            logger.error(f"Error persisting evidence: {e}")
            raise e

    def get_evidence(self, evidence_id: str) -> Optional[EvidencePackage]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence_packages WHERE evidence_id = ?", (evidence_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._map_row(row)
        
    def get_by_security_event_id(self, security_event_id: str) -> Optional[EvidencePackage]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence_packages WHERE security_event_id = ?", (security_event_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._map_row(row)

    def update_evidence_status(self, evidence_id: str, status: EvidenceStatus):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE evidence_packages SET status = ? WHERE evidence_id = ?", (status.value, evidence_id))
        conn.commit()
        
    def _map_row(self, row: sqlite3.Row) -> EvidencePackage:
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        # Parse standard nested domain objects out of metadata
        # Re-construct EvidencePackage
        return EvidencePackage(
            evidence_id=row["evidence_id"],
            security_event_id=row["security_event_id"],
            alert_id=row["alert_id"],
            camera_id=row["camera_id"],
            track_id=row["track_id"],
            event_type=row["event_type"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            evidence_quality=EvidenceQuality(row["evidence_quality"]) if row["evidence_quality"] else None,
            status=EvidenceStatus(row["status"]),
            original_frame_path=row["original_frame_path"],
            annotated_frame_reference=row["annotated_frame_reference"],
            metadata=metadata,
            failure_reason=metadata.get("failure_reason"),
            created_at=datetime.fromisoformat(row["created_at"])
        )
