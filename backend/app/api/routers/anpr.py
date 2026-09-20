"""
IBVAP API — ANPR Router
=========================
REST endpoints for ANPR (Automatic Number Plate Recognition) intelligence.

Endpoints:
    GET  /api/v1/anpr/reads          — List ANPR detections
    GET  /api/v1/anpr/reads/{plate}  — Search by plate number
    GET  /api/v1/anpr/status         — ANPR module status
    GET  /api/v1/anpr/summary        — ANPR summary statistics
"""

import json
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from app.infrastructure.database import SQLiteDatabase
from app.config import settings

router = APIRouter(prefix="/anpr", tags=["anpr"])
db = SQLiteDatabase()


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@router.get("/status", summary="ANPR module status")
async def anpr_status():
    """Returns the current status and configuration of the ANPR module."""
    return {
        "enabled": getattr(settings, "anpr_enabled", True),
        "detector_model": getattr(settings, "anpr_detector_model_path", "best.pt"),
        "detector_confidence": getattr(settings, "anpr_detector_confidence", 0.50),
        "consensus_threshold": getattr(settings, "anpr_consensus_threshold", 3),
        "min_vehicle_width": getattr(settings, "anpr_min_vehicle_width", 100),
        "min_plate_width": getattr(settings, "anpr_min_plate_width", 40),
        "ocr_engine": "Awiros/PaddleOCR",
        "validation_pattern": "Indian Standard (XX00XX0000)",
    }


@router.get("/summary", summary="ANPR summary statistics")
async def anpr_summary():
    """Returns aggregate ANPR detection statistics."""
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM anpr_reads")
    total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT vehicle_class, COUNT(*) as count
        FROM anpr_reads
        GROUP BY vehicle_class
    """)
    by_vehicle = {row["vehicle_class"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT camera_id, COUNT(*) as count
        FROM anpr_reads
        GROUP BY camera_id
        ORDER BY count DESC
    """)
    by_camera = {row["camera_id"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("SELECT COUNT(DISTINCT plate_text) as unique_plates FROM anpr_reads")
    unique_plates = cursor.fetchone()["unique_plates"]

    return {
        "total_reads": total,
        "unique_plates": unique_plates,
        "by_vehicle_class": by_vehicle,
        "by_camera": by_camera,
    }


@router.get("/reads", summary="List ANPR detections")
async def list_anpr_reads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    camera_id: Optional[str] = None,
    vehicle_class: Optional[str] = None,
    plate: Optional[str] = None,
):
    """List ANPR detections with optional filters."""
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    query = "SELECT * FROM anpr_reads WHERE 1=1"
    params = []

    if camera_id:
        query += " AND camera_id = ?"
        params.append(camera_id)
    if vehicle_class:
        query += " AND vehicle_class = ?"
        params.append(vehicle_class)
    if plate:
        query += " AND plate_text LIKE ?"
        params.append(f"%{plate}%")

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    for row in rows:
        if row.get("evidence"):
            try:
                row["evidence"] = json.loads(row["evidence"])
            except Exception:
                pass

    return rows


@router.get("/reads/{plate_text}", summary="Search by plate number")
async def search_plate(plate_text: str):
    """Search for all ANPR reads matching a specific plate number."""
    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM anpr_reads WHERE plate_text LIKE ? ORDER BY timestamp DESC",
        (f"%{plate_text}%",),
    )
    rows = cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No ANPR reads found for plate: {plate_text}")

    for row in rows:
        if row.get("evidence"):
            try:
                row["evidence"] = json.loads(row["evidence"])
            except Exception:
                pass

    return rows

import os
from fastapi.responses import FileResponse

def get_safe_path(base_dir: str, target_path: str) -> str:
    # Ensure the path exists and is within the base directory to prevent path traversal
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(target_path)
    if not abs_target.startswith(abs_base):
        raise HTTPException(status_code=403, detail="Path traversal detected")
    if not os.path.exists(abs_target):
        raise HTTPException(status_code=404, detail="Artifact not found")
    return abs_target

@router.get("/evidence/{event_id}/{image_type}", summary="Get ANPR evidence image")
async def get_anpr_evidence(event_id: str, image_type: str):
    """
    Get an evidence image for an ANPR event.
    image_type can be: 'plate', 'vehicle', 'full'
    """
    if image_type not in ["plate", "vehicle", "full"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    conn = db.get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    cursor.execute("SELECT evidence FROM anpr_reads WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()

    if not row or not row.get("evidence"):
        raise HTTPException(status_code=404, detail="Evidence not found")

    try:
        evidence_data = json.loads(row["evidence"])
        artifacts = evidence_data.get("artifacts", {})
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid evidence data")

    image_key = f"{image_type}_crop" if image_type in ["plate", "vehicle"] else "full_frame"
    img_path = artifacts.get(image_key)

    if not img_path:
        raise HTTPException(status_code=404, detail="Requested image type not found in evidence")

    safe_path = get_safe_path(settings.storage_base_path, img_path)
    return FileResponse(safe_path, media_type="image/jpeg")
