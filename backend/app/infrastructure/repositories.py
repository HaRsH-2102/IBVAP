import json
import logging
from typing import Optional, List
from datetime import datetime

from app.domain.security import SecurityEvent, Alert, AlertStatus, EvidencePackage
from app.domain.rule import Severity
from app.infrastructure.database import SQLiteDatabase

logger = logging.getLogger("IBVAP.Repositories")

class SecurityEventRepository:
    def __init__(self, db: SQLiteDatabase):
        self.db = db
        
    def save(self, event: SecurityEvent):
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_events (
                    event_id, source_spatial_event_id, rule_id, event_type, 
                    severity, camera_id, track_id, timestamp, correlation_id, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.source_spatial_event_id,
                event.rule_id,
                event.event_type,
                event.severity.value,
                event.camera_id,
                event.track_id,
                event.timestamp.isoformat(),
                event.correlation_id,
                json.dumps(event.metadata),
                datetime.utcnow().isoformat()
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save SecurityEvent {event.event_id}: {e}")
            raise

class AlertRepository:
    def __init__(self, db: SQLiteDatabase):
        self.db = db
        
    def _row_to_alert(self, row) -> Alert:
        # Convert SQLite row to Alert object
        return Alert(
            alert_id=row['alert_id'],
            severity=Severity(row['severity']),
            event_type=row['event_type'],
            camera_id=row['camera_id'],
            track_id=row['track_id'],
            rule_id=row['rule_id'],
            spatial_object_id=row['spatial_object_id'],
            status=AlertStatus(row['status']),
            title=row['title'],
            description=row['description'],
            correlation_id=row['correlation_id'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] else None,
            metadata=json.loads(row['metadata']),
            security_event_ids=json.loads(row['security_event_ids'])
        )

    def get_active_alert_by_dedup_key(self, dedup_key: str) -> Optional[Alert]:
        """
        Retrieves an OPEN or ACKNOWLEDGED alert matching the dedup key.
        We extract the fields from the dedup_key to use the index efficiently.
        key format: camera_id:track_id:rule_id:spatial_object_id
        """
        try:
            parts = dedup_key.split(':')
            if len(parts) != 4:
                return None
            cam_id, trk_id, rule_id, obj_id = parts
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM alerts 
                WHERE camera_id = ? AND track_id = ? AND rule_id = ? AND spatial_object_id = ? 
                AND status IN ('OPEN', 'ACKNOWLEDGED')
                ORDER BY created_at DESC LIMIT 1
            """, (cam_id, trk_id, rule_id, obj_id))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_alert(row)
            return None
        except Exception as e:
            logger.error(f"Failed to lookup active alert: {e}")
            return None

    def save_alert(self, alert: Alert):
        """Inserts or updates an alert."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Use UPSERT logic
            cursor.execute("""
                INSERT INTO alerts (
                    alert_id, severity, event_type, camera_id, track_id, 
                    rule_id, spatial_object_id, status, title, description, 
                    correlation_id, created_at, updated_at, resolved_at, metadata, security_event_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alert_id) DO UPDATE SET
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    resolved_at=excluded.resolved_at,
                    security_event_ids=excluded.security_event_ids,
                    metadata=excluded.metadata
            """, (
                alert.alert_id,
                alert.severity.value,
                alert.event_type,
                alert.camera_id,
                alert.track_id,
                alert.rule_id,
                alert.spatial_object_id,
                alert.status.value,
                alert.title,
                alert.description,
                alert.correlation_id,
                alert.created_at.isoformat(),
                alert.updated_at.isoformat(),
                alert.resolved_at.isoformat() if alert.resolved_at else None,
                json.dumps(alert.metadata),
                json.dumps(alert.security_event_ids)
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save Alert {alert.alert_id}: {e}")
            raise
            
class EvidenceRepository:
    def __init__(self, db: SQLiteDatabase):
        self.db = db
        
    def _row_to_evidence(self, row) -> EvidencePackage:
        return EvidencePackage(
            evidence_id=row['evidence_id'],
            event_id=row['security_event_id'],
            camera_id=row['camera_id'],
            track_id=row['track_id'],
            frame_id=row['frame_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            event_type=row['event_type'],
            object_class=row['object_class'],
            bbox=json.loads(row['bbox']) if row['bbox'] else {},
            crop_path=row['crop_path'],
            full_frame_path=row['full_frame_path'],
            created_at=datetime.fromisoformat(row['created_at']),
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
            is_saved=bool(row['is_saved']),
            saved_at=datetime.fromisoformat(row['saved_at']) if row['saved_at'] else None
        )
        
    def save(self, ev: EvidencePackage):
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO evidence_packages (
                    evidence_id, security_event_id, camera_id, track_id, frame_id,
                    event_type, object_class, bbox, timestamp,
                    crop_path, full_frame_path, created_at, expires_at, is_saved, saved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evidence_id) DO UPDATE SET
                    is_saved=excluded.is_saved,
                    saved_at=excluded.saved_at,
                    expires_at=excluded.expires_at
            """, (
                ev.evidence_id,
                ev.event_id,
                ev.camera_id,
                ev.track_id,
                ev.frame_id,
                ev.event_type,
                ev.object_class,
                json.dumps(ev.bbox),
                ev.timestamp.isoformat(),
                ev.crop_path,
                ev.full_frame_path,
                ev.created_at.isoformat(),
                ev.expires_at.isoformat() if ev.expires_at else None,
                1 if ev.is_saved else 0,
                ev.saved_at.isoformat() if ev.saved_at else None
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save EvidencePackage {ev.evidence_id}: {e}")
            raise
            
    def get_by_event(self, event_id: str) -> Optional[EvidencePackage]:
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evidence_packages WHERE security_event_id = ?", (event_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_evidence(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get evidence for event {event_id}: {e}")
            return None
            
    def get_expired_evidence(self) -> List[EvidencePackage]:
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            # Select unsaved and expired
            now = datetime.utcnow().isoformat()
            cursor.execute("SELECT * FROM evidence_packages WHERE is_saved = 0 AND expires_at <= ?", (now,))
            rows = cursor.fetchall()
            return [self._row_to_evidence(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get expired evidence: {e}")
            return []
            
    def delete(self, evidence_id: str):
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM evidence_packages WHERE evidence_id = ?", (evidence_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to delete evidence {evidence_id}: {e}")
            raise
            
    def save_status(self, evidence_id: str, is_saved: bool):
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            if is_saved:
                cursor.execute("UPDATE evidence_packages SET is_saved = 1, saved_at = ?, expires_at = NULL WHERE evidence_id = ?", (now, evidence_id))
            else:
                # Should not be un-saving, but if needed, we might re-set expires_at
                pass
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save status for evidence {evidence_id}: {e}")
            raise
