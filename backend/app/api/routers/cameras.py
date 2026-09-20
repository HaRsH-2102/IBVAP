from __future__ import annotations
from typing import List, Dict, Any

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from app.infrastructure.database import SQLiteDatabase

router = APIRouter(prefix="/cameras", tags=["cameras"])
db = SQLiteDatabase()

# In-memory mock registry for M12 since M14 DB registry is deferred
MOCK_CAMERAS = {
    "cam_test_01": {
        "camera_id": "cam_test_01",
        "name": "Main Gate",
        "location": "North Entrance",
        "status": "ONLINE",
        "source_type": "IP",
        "scene_state": "DAY",
        "fps": 25.0,
        "last_frame_timestamp": None,
        "active_track_count": 8,
        "dropped_frames": 0,
        "processing_latency": 45
    },
    "cam_track": {
        "camera_id": "cam_track",
        "name": "Track Demo Camera",
        "location": "Test Lab",
        "status": "ONLINE",
        "source_type": "FILE",
        "scene_state": "NIGHT",
        "fps": 30.0,
        "last_frame_timestamp": None,
        "active_track_count": 2,
        "dropped_frames": 0,
        "processing_latency": 10
    }
}

def get_open_alerts_count(camera_id: str) -> int:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE camera_id = ? AND status = 'OPEN'", (camera_id,))
    row = cursor.fetchone()
    return row["count"] if row else 0

@router.get("", summary="List all cameras")
async def list_cameras():
    cameras_list = []
    
    # Check if there are other cameras in the DB that we don't have mocked
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT camera_id FROM alerts")
    db_cams = [r["camera_id"] for r in cursor.fetchall()]
    
    for cam_id in set(list(MOCK_CAMERAS.keys()) + db_cams):
        cam = MOCK_CAMERAS.get(cam_id, {
            "camera_id": cam_id,
            "name": f"Camera {cam_id}",
            "location": "Unknown",
            "status": "ONLINE",
            "scene_state": "DAY",
            "fps": 25.0,
            "active_track_count": 0
        }).copy()
        
        cam["alerts"] = get_open_alerts_count(cam_id)
        cameras_list.append(cam)
        
    return cameras_list


@router.get("/{camera_id}", summary="Get camera details")
async def get_camera(camera_id: str):
    cam = MOCK_CAMERAS.get(camera_id)
    if not cam:
        # Fallback for dynamic cameras in DB
        if get_open_alerts_count(camera_id) >= 0:
            cam = {
                "camera_id": camera_id,
                "name": f"Camera {camera_id}",
                "status": "ONLINE",
                "scene_state": "DAY",
                "fps": 25.0,
                "active_track_count": 0
            }
        else:
            raise HTTPException(status_code=404, detail="Camera not found")
            
    cam = dict(cam)
    cam["alerts"] = get_open_alerts_count(camera_id)
    return cam

@router.get("/{camera_id}/stream", summary="Get stream status")
async def get_stream_status(camera_id: str):
    return {"status": "ONLINE", "stream_url": "N/A - Uses periodic snapshots"}

@router.get("/{camera_id}/snapshot", summary="Get live camera snapshot")
async def get_camera_snapshot(camera_id: str):
    import os
    from fastapi.responses import FileResponse
    from app.config import settings
    
    snapshot_path = os.path.abspath(os.path.join(settings.storage_base_path, f"latest_{camera_id}.jpg"))
    if not os.path.exists(snapshot_path):
        raise HTTPException(status_code=404, detail="Snapshot unavailable")
        
    return FileResponse(snapshot_path, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})
