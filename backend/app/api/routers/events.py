"""
IBVAP API — Events Router
===========================
REST endpoints for security event management.

Endpoints:
    GET  /api/v1/events              — List events (filterable)
    GET  /api/v1/events/{id}         — Get event details
    GET  /api/v1/events/{id}/evidence — Get event evidence
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from app.infrastructure.database import SQLiteDatabase

router = APIRouter(prefix="/events", tags=["events"])
db = SQLiteDatabase()


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@router.get("", summary="List security events")
async def list_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    camera_id: Optional[str] = None,
    track_id: Optional[str] = None,
    rule_id: Optional[str] = None,
):
    """List security events with optional filters."""
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    query = "SELECT * FROM security_events WHERE 1=1"
    params = []

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if camera_id:
        query += " AND camera_id = ?"
        params.append(camera_id)
    if track_id:
        query += " AND track_id = ?"
        params.append(track_id)
    if rule_id:
        query += " AND rule_id = ?"
        params.append(rule_id)

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if rows:
        event_ids = [r["event_id"] for r in rows]
        placeholders = ",".join("?" * len(event_ids))
        
        # Batch fetch evidence
        cursor.execute(f"SELECT * FROM evidence_packages WHERE security_event_id IN ({placeholders})", event_ids)
        evidence_rows = cursor.fetchall()
        evidence_map = {e["security_event_id"]: e for e in evidence_rows}
        
        # Batch fetch ANPR
        cursor.execute(f"SELECT * FROM anpr_reads WHERE event_id IN ({placeholders})", event_ids)
        anpr_rows = cursor.fetchall()
        anpr_map = {a["event_id"]: a for a in anpr_rows}

        for row in rows:
            if row.get("metadata"):
                try:
                    row["metadata"] = json.loads(row["metadata"])
                except Exception:
                    pass
            
            row["evidence"] = evidence_map.get(row["event_id"])
            row["anpr"] = anpr_map.get(row["event_id"])

    return rows


@router.get("/summary", summary="Event summary statistics")
async def event_summary():
    """Returns aggregate counts of security events by type and severity."""
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    cursor.execute("""
        SELECT event_type, severity, COUNT(*) as count
        FROM security_events
        GROUP BY event_type, severity
        ORDER BY count DESC
    """)
    by_type = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) as total FROM security_events")
    total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT severity, COUNT(*) as count
        FROM security_events
        GROUP BY severity
    """)
    by_severity = {row["severity"]: row["count"] for row in cursor.fetchall()}

    return {
        "total_events": total,
        "by_severity": by_severity,
        "by_type_severity": by_type,
    }


@router.get("/{event_id}", summary="Get event details")
async def get_event(event_id: str):
    """Get details of a specific security event."""
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM security_events WHERE event_id = ?", (event_id,))
    event = cursor.fetchone()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.get("metadata"):
        try:
            event["metadata"] = json.loads(event["metadata"])
        except Exception:
            pass

    # Fetch associated evidence if exists
    cursor.execute("SELECT * FROM evidence_packages WHERE security_event_id = ?", (event_id,))
    evidence = cursor.fetchone()
    if evidence:
        event["evidence"] = evidence

    # Fetch associated clip if exists
    cursor.execute("SELECT * FROM incident_clips WHERE security_event_id = ?", (event_id,))
    clip = cursor.fetchone()
    if clip:
        event["clip"] = clip

    # Fetch associated ANPR if exists
    cursor.execute("SELECT * FROM anpr_reads WHERE event_id = ?", (event_id,))
    anpr = cursor.fetchone()
    event["anpr"] = anpr if anpr else None

    return event


@router.get("/{event_id}/evidence", summary="Get event evidence image")
async def get_event_evidence(event_id: str, type: str = "crop"):
    """Get evidence image associated with a security event."""
    from fastapi.responses import FileResponse
    import os

    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    path = None
    if type == "plate":
        cursor.execute("SELECT plate_crop_path FROM anpr_reads WHERE event_id = ?", (event_id,))
        anpr = cursor.fetchone()
        if not anpr or not anpr.get("plate_crop_path"):
            raise HTTPException(status_code=404, detail="No plate crop found for this event")
        path = anpr.get("plate_crop_path")
    else:
        cursor.execute("SELECT crop_path, full_frame_path FROM evidence_packages WHERE security_event_id = ?", (event_id,))
        evidence = cursor.fetchone()

        if not evidence:
            raise HTTPException(status_code=404, detail="No evidence found for this event")
        path = evidence.get("full_frame_path") if type == "full" else evidence.get("crop_path")
        
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Evidence image file not found")

    return FileResponse(path)

class PlateOverrideRequest(BaseModel):
    plate_text: str

@router.post("/{event_id}/override_plate", summary="Manual operator plate entry")
async def override_plate(event_id: str, req: PlateOverrideRequest):
    """SIH Demo Feature: Manually associate a plate with an event without destroying AI results."""
    plate = req.plate_text.strip().upper()
    if not plate:
        raise HTTPException(status_code=400, detail="Invalid plate text")
        
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Ensure event exists
    cursor.execute("SELECT camera_id, track_id, timestamp, metadata FROM security_events WHERE event_id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    cursor.execute("SELECT * FROM anpr_reads WHERE event_id = ?", (event_id,))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE anpr_reads 
            SET operator_plate_text = ?, entry_source = 'OPERATOR' 
            WHERE event_id = ?
        """, (plate, event_id))
    else:
        import json
        vehicle_class = ""
        metadata = event["metadata"] if isinstance(event, dict) else event["metadata"]
        if metadata:
            try:
                meta = json.loads(metadata)
                vehicle_class = meta.get("object_class", "")
            except: pass
            
        cursor.execute("""
            INSERT INTO anpr_reads (
                event_id, camera_id, track_id, plate_text, vehicle_class, timestamp, 
                created_at, status, entry_source, operator_plate_text
            ) VALUES (?, ?, ?, '', ?, ?, datetime('now'), 'NO_AI_DATA', 'OPERATOR', ?)
        """, (event_id, event["camera_id"], event["track_id"], vehicle_class, event["timestamp"], plate))
        
    conn.commit()
    return {"status": "success", "event_id": event_id, "operator_plate_text": plate}
