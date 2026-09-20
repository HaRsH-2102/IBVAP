import os
import uuid
from datetime import datetime
import cv2
import av
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
from app.infrastructure.database import SQLiteDatabase

router = APIRouter(prefix="/videos", tags=["videos"])

class VideoSource(BaseModel):
    id: str
    name: str
    file_path: str
    resolution: Optional[str] = None
    duration_sec: Optional[float] = None
    container: Optional[str] = None
    codec: Optional[str] = None
    fps: Optional[float] = None
    created_at: str

class VideoAddRequest(BaseModel):
    name: str
    file_path: str

@router.get("", response_model=List[VideoSource])
def list_videos():
    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM video_sources ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return [VideoSource(**dict(r)) for r in rows]

@router.post("", response_model=VideoSource)
def add_video(req: VideoAddRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    # 1. Inspect actual media metadata using PyAV
    try:
        container_av = av.open(req.file_path)
        v_streams = container_av.streams.video
        if not v_streams:
            container_av.close()
            raise HTTPException(status_code=400, detail="No video stream found in file")
        v_stream = v_streams[0]
        
        container_name = container_av.format.long_name if container_av.format else "Unknown"
        codec_name = v_stream.codec_context.codec.long_name if v_stream.codec_context and v_stream.codec_context.codec else "Unknown"
        
        width = v_stream.width
        height = v_stream.height
        fps = float(v_stream.average_rate) if v_stream.average_rate else 0.0
        frame_count = v_stream.frames
        container_av.close()
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Video codec/container is not supported by the current decoder. Reason: {e}"
        )

    # 2. Verify that OpenCV can read at least one frame
    cap = cv2.VideoCapture(req.file_path)
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Cannot open video file with OpenCV pipeline backend")
        
    ret, frame = cap.read()
    cap.release()
    
    if not ret or frame is None:
        raise HTTPException(status_code=400, detail="Failed to decode the first frame. The OpenCV FFmpeg backend might lack support for this codec.")

    resolution = f"{width}x{height}" if width and height else None
    duration_sec = frame_count / fps if fps > 0 else None

    vid_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO video_sources (id, name, file_path, resolution, duration_sec, container, codec, fps, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (vid_id, req.name, req.file_path, resolution, duration_sec, container_name, codec_name, fps, now)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return VideoSource(
        id=vid_id, name=req.name, file_path=req.file_path, 
        resolution=resolution, duration_sec=duration_sec, 
        container=container_name, codec=codec_name, fps=fps, created_at=now
    )

@router.delete("/{video_id}")
def delete_video(video_id: str):
    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM video_sources WHERE id = ?", (video_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Also delete associated zones and lines
    cursor.execute("DELETE FROM spatial_zones WHERE camera_id = ?", (video_id,))
    cursor.execute("DELETE FROM virtual_lines WHERE camera_id = ?", (video_id,))
    
    conn.commit()
    return {"status": "deleted"}

@router.get("/{video_id}/frame")
def get_video_frame(video_id: str):
    db = SQLiteDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM video_sources WHERE id = ?", (video_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")
        
    file_path = row["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file missing on server")

    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="Could not open video file")
        
    ret, frame = cap.read()
    cap.release()
    
    if not ret or frame is None:
        raise HTTPException(status_code=500, detail="Could not read first frame")

    # Encode frame to JPEG
    ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ret:
        raise HTTPException(status_code=500, detail="Could not encode frame")
        
    return Response(content=buffer.tobytes(), media_type="image/jpeg")
