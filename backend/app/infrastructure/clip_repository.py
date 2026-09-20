import json
from typing import Optional
import logging
from datetime import datetime

from app.domain.incident_clip import IncidentClip, ClipStatus
from app.infrastructure.database import SQLiteDatabase

logger = logging.getLogger("IBVAP.ClipRepository")

class SQLiteClipRepository:
    def __init__(self, db: SQLiteDatabase):
        self.db = db
        
    def create_clip(self, clip: IncidentClip) -> bool:
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO incident_clips (
                    clip_id, security_event_id, alert_id, evidence_id, camera_id,
                    track_id, event_type, event_timestamp, clip_start_timestamp,
                    clip_end_timestamp, pre_event_seconds, post_event_seconds,
                    duration_seconds, source_video_reference, clip_path,
                    thumbnail_path, status, failure_reason, created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                clip.clip_id, clip.security_event_id, clip.alert_id, clip.evidence_id, clip.camera_id,
                clip.track_id, clip.event_type, 
                clip.event_timestamp.isoformat() if clip.event_timestamp else None,
                clip.clip_start_timestamp.isoformat() if clip.clip_start_timestamp else None,
                clip.clip_end_timestamp.isoformat() if clip.clip_end_timestamp else None,
                clip.pre_event_seconds, clip.post_event_seconds, clip.duration_seconds,
                clip.source_video_reference, clip.clip_path, clip.thumbnail_path,
                clip.status.value, clip.failure_reason,
                clip.created_at.isoformat(),
                json.dumps(clip.metadata) if clip.metadata else "{}"
            ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to create clip for event {clip.security_event_id}: {e}")
            raise
            
    def update_clip(self, clip: IncidentClip) -> bool:
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE incident_clips SET 
                    status = ?, 
                    clip_path = ?,
                    thumbnail_path = ?,
                    failure_reason = ?,
                    clip_start_timestamp = ?,
                    clip_end_timestamp = ?,
                    duration_seconds = ?,
                    metadata = ?
                WHERE clip_id = ?
            """, (
                clip.status.value, clip.clip_path, clip.thumbnail_path, clip.failure_reason,
                clip.clip_start_timestamp.isoformat() if clip.clip_start_timestamp else None,
                clip.clip_end_timestamp.isoformat() if clip.clip_end_timestamp else None,
                clip.duration_seconds,
                json.dumps(clip.metadata) if clip.metadata else "{}",
                clip.clip_id
            ))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update clip {clip.clip_id}: {e}")
            raise
            
    def get_by_security_event_id(self, event_id: str) -> Optional[IncidentClip]:
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM incident_clips WHERE security_event_id = ?", (event_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return IncidentClip(
                clip_id=row['clip_id'],
                security_event_id=row['security_event_id'],
                alert_id=row['alert_id'],
                evidence_id=row['evidence_id'],
                camera_id=row['camera_id'],
                track_id=row['track_id'],
                event_type=row['event_type'],
                event_timestamp=datetime.fromisoformat(row['event_timestamp']) if row['event_timestamp'] else None,
                clip_start_timestamp=datetime.fromisoformat(row['clip_start_timestamp']) if row['clip_start_timestamp'] else None,
                clip_end_timestamp=datetime.fromisoformat(row['clip_end_timestamp']) if row['clip_end_timestamp'] else None,
                pre_event_seconds=row['pre_event_seconds'],
                post_event_seconds=row['post_event_seconds'],
                duration_seconds=row['duration_seconds'],
                source_video_reference=row['source_video_reference'],
                clip_path=row['clip_path'],
                thumbnail_path=row['thumbnail_path'],
                status=ClipStatus(row['status']),
                failure_reason=row['failure_reason'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                metadata=json.loads(row['metadata']) if row['metadata'] else {}
            )
        except Exception as e:
            logger.error(f"Failed to get clip for event {event_id}: {e}")
            raise
