"""
IBVAP API — Zones Router
==========================
REST endpoints for zone and virtual line configuration.

Endpoints:
    GET    /api/v1/zones               — List all zones (optional ?camera_id=)
    POST   /api/v1/zones               — Create zone
    GET    /api/v1/zones/{id}          — Get zone details
    PATCH  /api/v1/zones/{id}          — Update zone
    DELETE /api/v1/zones/{id}          — Delete zone
    GET    /api/v1/zones/lines         — List virtual lines (optional ?camera_id=)
    POST   /api/v1/zones/lines         — Create virtual line
    PATCH  /api/v1/zones/lines/{id}    — Update virtual line
    DELETE /api/v1/zones/lines/{id}    — Delete virtual line
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.infrastructure.database import SQLiteDatabase

router = APIRouter(prefix="/zones", tags=["zones"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class PointModel(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class CreateZoneRequest(BaseModel):
    name: str
    camera_id: str
    zone_type: str = "RESTRICTED"
    geometry: list[PointModel]
    configuration: dict = Field(default_factory=dict)


class UpdateZoneRequest(BaseModel):
    name: str | None = None
    zone_type: str | None = None
    geometry: list[PointModel] | None = None
    active: bool | None = None
    configuration: dict | None = None


class CreateLineRequest(BaseModel):
    name: str
    camera_id: str
    points: list[PointModel]
    allowed_direction: str = "BOTH"
    configuration: dict = Field(default_factory=dict)


class UpdateLineRequest(BaseModel):
    name: str | None = None
    points: list[PointModel] | None = None
    allowed_direction: str | None = None
    active: bool | None = None
    configuration: dict | None = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_db():
    return SQLiteDatabase()


def _row_to_zone(row) -> dict:
    return {
        "zone_id": row["zone_id"],
        "camera_id": row["camera_id"],
        "name": row["name"],
        "zone_type": row["zone_type"],
        "geometry": json.loads(row["geometry"]),
        "active": bool(row["active"]),
        "configuration": json.loads(row["configuration"] or "{}"),
        "created_at": row["created_at"],
    }


def _row_to_line(row) -> dict:
    return {
        "line_id": row["line_id"],
        "camera_id": row["camera_id"],
        "name": row["name"],
        "points": json.loads(row["points"]),
        "allowed_direction": row["allowed_direction"],
        "active": bool(row["active"]),
        "configuration": json.loads(row["configuration"] or "{}"),
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Zone Endpoints
# ---------------------------------------------------------------------------

@router.get("", summary="List all zones")
async def list_zones(camera_id: str | None = Query(None)):
    db = _get_db()
    conn = db.get_connection()
    if camera_id:
        rows = conn.execute("SELECT * FROM spatial_zones WHERE camera_id = ? ORDER BY created_at", (camera_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM spatial_zones ORDER BY created_at").fetchall()
    return [_row_to_zone(r) for r in rows]


@router.post("", summary="Create zone", status_code=201)
async def create_zone(req: CreateZoneRequest):
    if len(req.geometry) < 3:
        raise HTTPException(status_code=400, detail="Polygon requires at least 3 points")

    db = _get_db()
    conn = db.get_connection()
    zone_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO spatial_zones (zone_id, camera_id, name, zone_type, geometry, active, configuration, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (zone_id, req.camera_id, req.name, req.zone_type, json.dumps([p.model_dump() for p in req.geometry]), 1, json.dumps(req.configuration), now)
    )
    conn.commit()

    return {
        "zone_id": zone_id,
        "camera_id": req.camera_id,
        "name": req.name,
        "zone_type": req.zone_type,
        "geometry": [p.model_dump() for p in req.geometry],
        "active": True,
        "configuration": req.configuration,
        "created_at": now,
    }


@router.get("/{zone_id}", summary="Get zone details")
async def get_zone(zone_id: str):
    db = _get_db()
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM spatial_zones WHERE zone_id = ?", (zone_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Zone not found")
    return _row_to_zone(row)


@router.patch("/{zone_id}", summary="Update zone")
async def update_zone(zone_id: str, req: UpdateZoneRequest):
    db = _get_db()
    conn = db.get_connection()

    row = conn.execute("SELECT * FROM spatial_zones WHERE zone_id = ?", (zone_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Zone not found")

    updates = []
    params = []
    if req.name is not None:
        updates.append("name = ?")
        params.append(req.name)
    if req.zone_type is not None:
        updates.append("zone_type = ?")
        params.append(req.zone_type)
    if req.geometry is not None:
        if len(req.geometry) < 3:
            raise HTTPException(status_code=400, detail="Polygon requires at least 3 points")
        updates.append("geometry = ?")
        params.append(json.dumps([p.model_dump() for p in req.geometry]))
    if req.active is not None:
        updates.append("active = ?")
        params.append(1 if req.active else 0)
    if req.configuration is not None:
        updates.append("configuration = ?")
        params.append(json.dumps(req.configuration))

    if updates:
        params.append(zone_id)
        conn.execute(f"UPDATE spatial_zones SET {', '.join(updates)} WHERE zone_id = ?", params)
        conn.commit()

    updated = conn.execute("SELECT * FROM spatial_zones WHERE zone_id = ?", (zone_id,)).fetchone()
    return _row_to_zone(updated)


@router.delete("/{zone_id}", summary="Delete zone")
async def delete_zone(zone_id: str):
    db = _get_db()
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM spatial_zones WHERE zone_id = ?", (zone_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Zone not found")
    conn.execute("DELETE FROM spatial_zones WHERE zone_id = ?", (zone_id,))
    conn.commit()
    return {"deleted": True, "zone_id": zone_id}


# ---------------------------------------------------------------------------
# Virtual Line Endpoints
# ---------------------------------------------------------------------------

@router.get("/lines", summary="List virtual lines")
async def list_virtual_lines(camera_id: str | None = Query(None)):
    db = _get_db()
    conn = db.get_connection()
    if camera_id:
        rows = conn.execute("SELECT * FROM virtual_lines WHERE camera_id = ? ORDER BY created_at", (camera_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM virtual_lines ORDER BY created_at").fetchall()
    return [_row_to_line(r) for r in rows]


@router.post("/lines", summary="Create virtual line", status_code=201)
async def create_virtual_line(req: CreateLineRequest):
    if len(req.points) < 2:
        raise HTTPException(status_code=400, detail="Virtual line requires at least 2 points")

    db = _get_db()
    conn = db.get_connection()
    line_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO virtual_lines (line_id, camera_id, name, points, allowed_direction, active, configuration, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (line_id, req.camera_id, req.name, json.dumps([p.model_dump() for p in req.points]), req.allowed_direction, 1, json.dumps(req.configuration), now)
    )
    conn.commit()

    return {
        "line_id": line_id,
        "camera_id": req.camera_id,
        "name": req.name,
        "points": [p.model_dump() for p in req.points],
        "allowed_direction": req.allowed_direction,
        "active": True,
        "configuration": req.configuration,
        "created_at": now,
    }


@router.patch("/lines/{line_id}", summary="Update virtual line")
async def update_virtual_line(line_id: str, req: UpdateLineRequest):
    db = _get_db()
    conn = db.get_connection()

    row = conn.execute("SELECT * FROM virtual_lines WHERE line_id = ?", (line_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Virtual line not found")

    updates = []
    params = []
    if req.name is not None:
        updates.append("name = ?")
        params.append(req.name)
    if req.points is not None:
        if len(req.points) < 2:
            raise HTTPException(status_code=400, detail="Virtual line requires at least 2 points")
        updates.append("points = ?")
        params.append(json.dumps([p.model_dump() for p in req.points]))
    if req.allowed_direction is not None:
        updates.append("allowed_direction = ?")
        params.append(req.allowed_direction)
    if req.active is not None:
        updates.append("active = ?")
        params.append(1 if req.active else 0)
    if req.configuration is not None:
        updates.append("configuration = ?")
        params.append(json.dumps(req.configuration))

    if updates:
        params.append(line_id)
        conn.execute(f"UPDATE virtual_lines SET {', '.join(updates)} WHERE line_id = ?", params)
        conn.commit()

    updated = conn.execute("SELECT * FROM virtual_lines WHERE line_id = ?", (line_id,)).fetchone()
    return _row_to_line(updated)


@router.delete("/lines/{line_id}", summary="Delete virtual line")
async def delete_virtual_line(line_id: str):
    db = _get_db()
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM virtual_lines WHERE line_id = ?", (line_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Virtual line not found")
    conn.execute("DELETE FROM virtual_lines WHERE line_id = ?", (line_id,))
    conn.commit()
    return {"deleted": True, "line_id": line_id}
