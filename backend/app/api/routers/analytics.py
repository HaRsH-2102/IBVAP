import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from app.infrastructure.database import SQLiteDatabase

router = APIRouter(prefix="/analytics", tags=["analytics"])

class AnalyticsSummary(BaseModel):
    total_events: int
    active_incidents: int
    intrusions: int
    fence_crossings: int
    loitering: int
    evidence_captured: int

@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary():
    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as c FROM security_events")
    total_events = cursor.fetchone()["c"]
    
    cursor.execute("SELECT COUNT(*) as c FROM alerts WHERE status != 'RESOLVED'")
    active_incidents = cursor.fetchone()["c"]
    
    cursor.execute("SELECT COUNT(*) as c FROM security_events WHERE event_type = 'ZONE_ENTER' OR event_type = 'INTRUSION'")
    intrusions = cursor.fetchone()["c"]
    
    cursor.execute("SELECT COUNT(*) as c FROM security_events WHERE event_type = 'LINE_CROSS'")
    fence_crossings = cursor.fetchone()["c"]
    
    cursor.execute("SELECT COUNT(*) as c FROM security_events WHERE event_type = 'LOITERING'")
    loitering = cursor.fetchone()["c"]
    
    cursor.execute("SELECT COUNT(*) as c FROM evidence_packages WHERE is_saved = 1")
    evidence_captured = cursor.fetchone()["c"]
    
    return AnalyticsSummary(
        total_events=total_events,
        active_incidents=active_incidents,
        intrusions=intrusions,
        fence_crossings=fence_crossings,
        loitering=loitering,
        evidence_captured=evidence_captured
    )

@router.get("/trends")
def get_analytics_trends():
    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 1. Events over time (by hour)
    cursor.execute("""
        SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour, COUNT(*) as count 
        FROM security_events 
        GROUP BY hour 
        ORDER BY hour ASC 
        LIMIT 24
    """)
    events_over_time = [{"hour": row["hour"], "count": row["count"]} for row in cursor.fetchall()]
    
    # 2. Events by type
    cursor.execute("SELECT event_type, COUNT(*) as count FROM security_events GROUP BY event_type")
    events_by_type = [{"type": row["event_type"], "count": row["count"]} for row in cursor.fetchall()]
    
    # 3. Object Class (Person vs Vehicle). Need to join tracks or assume from metadata/alerts if possible.
    # We might not have class in security_events easily unless it's in metadata JSON.
    # For now, let's look at recent alerts which have description or title with object class.
    # Alternatively, if we just parse the `metadata` JSON column. SQLite JSON1 extension is standard.
    cursor.execute("""
        SELECT 
            json_extract(metadata, '$.object_class') as obj_class,
            COUNT(*) as count
        FROM security_events
        WHERE json_extract(metadata, '$.object_class') IS NOT NULL
        GROUP BY obj_class
    """)
    rows = cursor.fetchall()
    events_by_class = [{"class": r["obj_class"], "count": r["count"]} for r in rows]
    
    # If no object_class in metadata, we might need a fallback.
    if not events_by_class:
        # Fallback to checking title of alerts
        cursor.execute("SELECT COUNT(*) as c FROM alerts WHERE title LIKE '%Person%'")
        persons = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) as c FROM alerts WHERE title LIKE '%Vehicle%' OR title LIKE '%Car%'")
        vehicles = cursor.fetchone()["c"]
        if persons > 0 or vehicles > 0:
            events_by_class = [
                {"class": "person", "count": persons},
                {"class": "vehicle", "count": vehicles}
            ]

    # 4. Events by Camera/Video
    cursor.execute("""
        SELECT 
            coalesce(v.name, s.camera_id) as camera_name,
            COUNT(*) as count
        FROM security_events s
        LEFT JOIN video_sources v ON s.camera_id = v.id
        GROUP BY camera_name
    """)
    events_by_camera = [{"camera": row["camera_name"], "count": row["count"]} for row in cursor.fetchall()]

    return {
        "over_time": events_over_time,
        "by_type": events_by_type,
        "by_class": events_by_class,
        "by_camera": events_by_camera
    }
