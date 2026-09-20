import sqlite3
import os
import logging
from threading import local

logger = logging.getLogger("IBVAP.Database")

class SQLiteDatabase:
    """
    Manages SQLite connections and schema initialization.
    Thread-local storage is used to ensure one connection per thread.
    """
    def __init__(self, db_path: str = None):
        if db_path is None:
            from app.config import settings
            db_path = settings.sqlite_db_path
        self.db_path = db_path
        self._local = local()
        self.init_schema()
        
    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            # Check_same_thread=False allows us to share connection if strictly needed, 
            # but we use thread locals to be safe.
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
        
    def close(self):
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
            
    def init_schema(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Concurrency settings for Evidence Worker (M10)
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            
            # Video Sources Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    resolution TEXT,
                    duration_sec REAL,
                    container TEXT,
                    codec TEXT,
                    fps REAL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Migrations for existing database
            try:
                cursor.execute("ALTER TABLE video_sources ADD COLUMN container TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists
                
            try:
                cursor.execute("ALTER TABLE video_sources ADD COLUMN codec TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists
                
            try:
                cursor.execute("ALTER TABLE video_sources ADD COLUMN fps REAL")
            except sqlite3.OperationalError:
                pass # Column already exists

            # Security Events Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id TEXT PRIMARY KEY,
                    source_spatial_event_id TEXT,
                    rule_id TEXT,
                    event_type TEXT,
                    severity TEXT,
                    camera_id TEXT,
                    track_id TEXT,
                    timestamp TEXT,
                    correlation_id TEXT,
                    metadata TEXT,
                    created_at TEXT
                )
            """)
            
            # Alerts Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    severity TEXT,
                    event_type TEXT,
                    camera_id TEXT,
                    track_id TEXT,
                    rule_id TEXT,
                    spatial_object_id TEXT,
                    status TEXT,
                    title TEXT,
                    description TEXT,
                    correlation_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    resolved_at TEXT,
                    metadata TEXT,
                    security_event_ids TEXT -- JSON list of IDs
                )
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sec_cam_trk ON security_events (camera_id, track_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sec_rule ON security_events (rule_id)")
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_cam_trk ON alerts (camera_id, track_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts (status)")
            # Dedup lookup index
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_dedup ON alerts (camera_id, track_id, rule_id, spatial_object_id)")
            
            # Evidence Packages Table (M10)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evidence_packages (
                    evidence_id TEXT PRIMARY KEY,
                    security_event_id TEXT UNIQUE NOT NULL,
                    alert_id TEXT,
                    camera_id TEXT,
                    track_id TEXT,
                    frame_id TEXT,
                    event_type TEXT,
                    object_class TEXT,
                    bbox TEXT,
                    timestamp TEXT,
                    evidence_quality TEXT,
                    status TEXT,
                    crop_path TEXT,
                    full_frame_path TEXT,
                    original_frame_path TEXT,
                    annotated_frame_reference TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    expires_at TEXT,
                    is_saved BOOLEAN DEFAULT 0,
                    saved_at TEXT
                )
            """)
            
            # Idempotent schema migration for existing databases
            new_columns = [
                ("frame_id", "TEXT"),
                ("object_class", "TEXT"),
                ("bbox", "TEXT"),
                ("crop_path", "TEXT"),
                ("full_frame_path", "TEXT"),
                ("expires_at", "TEXT"),
                ("is_saved", "BOOLEAN DEFAULT 0"),
                ("saved_at", "TEXT")
            ]
            for col_name, col_type in new_columns:
                try:
                    cursor.execute(f"ALTER TABLE evidence_packages ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    # Column likely already exists
                    pass
                    
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_event ON evidence_packages (security_event_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_expires ON evidence_packages (is_saved, expires_at)")
            # Incident Clips Table (M11)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incident_clips (
                    clip_id TEXT PRIMARY KEY,
                    security_event_id TEXT UNIQUE NOT NULL,
                    alert_id TEXT,
                    evidence_id TEXT,
                    camera_id TEXT,
                    track_id TEXT,
                    event_type TEXT,
                    event_timestamp TEXT,
                    clip_start_timestamp TEXT,
                    clip_end_timestamp TEXT,
                    pre_event_seconds REAL,
                    post_event_seconds REAL,
                    duration_seconds REAL,
                    source_video_reference TEXT,
                    clip_path TEXT,
                    thumbnail_path TEXT,
                    status TEXT,
                    failure_reason TEXT,
                    created_at TEXT,
                    metadata TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clip_event ON incident_clips (security_event_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clip_camera ON incident_clips (camera_id)")
            
            # ANPR Reads Table (M9)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anpr_reads (
                    event_id TEXT PRIMARY KEY,
                    camera_id TEXT,
                    track_id TEXT,
                    plate_text TEXT NOT NULL,
                    confidence REAL,
                    vehicle_class TEXT,
                    timestamp TEXT,
                    evidence TEXT,
                    created_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anpr_plate ON anpr_reads (plate_text)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anpr_camera ON anpr_reads (camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anpr_timestamp ON anpr_reads (timestamp)")
            
            # Idempotent migration for new ANPR fields
            new_anpr_columns = [
                ("plate_text_raw", "TEXT"),
                ("plate_text_normalized", "TEXT"),
                ("plate_confidence", "REAL"),
                ("ocr_confidence", "REAL"),
                ("plate_bbox", "TEXT"),
                ("source_frame_path", "TEXT"),
                ("plate_crop_path", "TEXT"),
                ("vehicle_crop_path", "TEXT"),
                ("consensus_count", "INTEGER DEFAULT 1"),
                ("status", "TEXT DEFAULT 'SUCCESS'"),
                ("processing_latency_ms", "REAL"),
                ("entry_source", "TEXT DEFAULT 'SYSTEM'"),
                ("operator_plate_text", "TEXT")
            ]
            for col_name, col_type in new_anpr_columns:
                try:
                    cursor.execute(f"ALTER TABLE anpr_reads ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass
            
            # Spatial Zones Table (operator-drawn restricted areas)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spatial_zones (
                    zone_id TEXT PRIMARY KEY,
                    camera_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    zone_type TEXT DEFAULT 'RESTRICTED',
                    geometry TEXT NOT NULL,
                    active BOOLEAN DEFAULT 1,
                    configuration TEXT DEFAULT '{}',
                    created_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sz_camera ON spatial_zones (camera_id)")
            
            # Virtual Lines Table (operator-drawn fences/tripwires)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS virtual_lines (
                    line_id TEXT PRIMARY KEY,
                    camera_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    points TEXT NOT NULL,
                    allowed_direction TEXT DEFAULT 'BOTH',
                    active BOOLEAN DEFAULT 1,
                    configuration TEXT DEFAULT '{}',
                    created_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vl_camera ON virtual_lines (camera_id)")
            
            conn.commit()
            logger.info(f"SQLite schema initialized successfully at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite schema: {e}")
            raise
