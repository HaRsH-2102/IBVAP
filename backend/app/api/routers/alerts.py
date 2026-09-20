import json
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.infrastructure.database import SQLiteDatabase

router = APIRouter(prefix="/alerts", tags=["alerts"])
db = SQLiteDatabase()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@router.get("", summary="List active alerts")
async def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    camera_id: Optional[str] = None
):
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    query = "SELECT * FROM alerts WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if camera_id:
        query += " AND camera_id = ?"
        params.append(camera_id)
        
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Parse metadata if present
    for row in rows:
        if row.get("metadata"):
            try:
                row["metadata"] = json.loads(row["metadata"])
            except:
                pass
                
    return rows

@router.get("/summary", summary="Alert summary statistics")
async def alert_summary():
    """Returns aggregate counts of alerts by severity and status."""
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM alerts")
    total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT severity, COUNT(*) as count
        FROM alerts
        GROUP BY severity
    """)
    by_severity = {row["severity"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM alerts
        GROUP BY status
    """)
    by_status = {row["status"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT COUNT(*) as count FROM alerts WHERE status IN ('OPEN', 'ACKNOWLEDGED')
    """)
    active = cursor.fetchone()["count"]

    return {
        "total_alerts": total,
        "active_alerts": active,
        "by_severity": by_severity,
        "by_status": by_status,
    }


@router.get("/{alert_id}", summary="Get alert details")
async def get_alert(alert_id: str):
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
    alert = cursor.fetchone()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if alert.get("metadata"):
        try:
            alert["metadata"] = json.loads(alert["metadata"])
        except:
            pass
            
    # Try to fetch associated evidence and clips using the primary security_event_id
    sec_ids_str = alert.get("security_event_ids", "[]")
    try:
        sec_ids = json.loads(sec_ids_str)
    except:
        sec_ids = []
        
    primary_event_id = sec_ids[0] if sec_ids else None
    
    if primary_event_id:
        cursor.execute("SELECT * FROM evidence_packages WHERE security_event_id = ?", (primary_event_id,))
        evd = cursor.fetchone()
        if evd:
            alert["evidence"] = evd
            
        cursor.execute("SELECT * FROM incident_clips WHERE security_event_id = ?", (primary_event_id,))
        clip = cursor.fetchone()
        if clip:
            alert["clip"] = clip
            
    return alert

@router.patch("/{alert_id}/ack", summary="Acknowledge alert")
async def acknowledge_alert(alert_id: str):
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Idempotent state transition
    cursor.execute("SELECT status FROM alerts WHERE alert_id = ?", (alert_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    current_status = row["status"] if isinstance(row, dict) else row[0]
    
    if current_status == "OPEN":
        cursor.execute("UPDATE alerts SET status = 'ACKNOWLEDGED' WHERE alert_id = ? AND status = 'OPEN'", (alert_id,))
        conn.commit()
        return {"alert_id": alert_id, "status": "ACKNOWLEDGED"}
    elif current_status == "ACKNOWLEDGED":
        return {"alert_id": alert_id, "status": "ACKNOWLEDGED"}
    else:
        raise HTTPException(status_code=400, detail=f"Cannot transition to ACKNOWLEDGED from {current_status}")

@router.patch("/{alert_id}/resolve", summary="Resolve alert")
async def resolve_alert(alert_id: str):
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM alerts WHERE alert_id = ?", (alert_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    current_status = row["status"] if isinstance(row, dict) else row[0]
    
    if current_status in ["OPEN", "ACKNOWLEDGED"]:
        cursor.execute("UPDATE alerts SET status = 'RESOLVED' WHERE alert_id = ? AND status IN ('OPEN', 'ACKNOWLEDGED')", (alert_id,))
        conn.commit()
        return {"alert_id": alert_id, "status": "RESOLVED"}
    elif current_status == "RESOLVED":
        return {"alert_id": alert_id, "status": "RESOLVED"}
    else:
        raise HTTPException(status_code=400, detail=f"Cannot transition to RESOLVED from {current_status}")
