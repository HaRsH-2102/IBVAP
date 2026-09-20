import os
import mimetypes
from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import FileResponse, Response, StreamingResponse
from app.infrastructure.database import SQLiteDatabase
from app.config import settings

router = APIRouter(tags=["artifacts"])
db = SQLiteDatabase()

def get_safe_path(base_dir: str, target_path: str) -> str:
    # Ensure the path exists and is within the base directory to prevent path traversal
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(target_path)
    if not abs_target.startswith(abs_base):
        raise HTTPException(status_code=403, detail="Path traversal detected")
    if not os.path.exists(abs_target):
        raise HTTPException(status_code=404, detail="Artifact not found")
    return abs_target

@router.get("/evidence/{evidence_id}/image", summary="Get annotated evidence image")
async def get_evidence_image(evidence_id: str):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT annotated_frame_reference, original_frame_path FROM evidence_packages WHERE evidence_id = ?", (evidence_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Evidence record not found")
        
    img_path = row[0] or row[1]
    if not img_path:
        raise HTTPException(status_code=404, detail="EVIDENCE UNAVAILABLE")
        
    safe_path = get_safe_path(settings.storage_base_path, img_path)
    return FileResponse(safe_path, media_type="image/jpeg")

@router.get("/clips/{clip_id}/thumbnail", summary="Get clip thumbnail")
async def get_clip_thumbnail(clip_id: str):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT thumbnail_path FROM incident_clips WHERE clip_id = ?", (clip_id,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
        
    safe_path = get_safe_path(settings.storage_base_path, row[0])
    return FileResponse(safe_path, media_type="image/jpeg")

@router.get("/clips/{clip_id}/video", summary="Stream incident clip (supports Range)")
async def get_clip_video(clip_id: str, request: Request, range: str = Header(None)):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT clip_path FROM incident_clips WHERE clip_id = ?", (clip_id,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    safe_path = get_safe_path(settings.storage_base_path, row[0])
    file_size = os.path.getsize(safe_path)
    
    if not range:
        return FileResponse(
            safe_path, 
            media_type="video/mp4",
            headers={"Accept-Ranges": "bytes"}
        )
        
    # Process Range header
    try:
        range_str = range.replace("bytes=", "")
        start_str, end_str = range_str.split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        
        if start >= file_size or end >= file_size:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
            
        chunk_size = end - start + 1
        
        def file_iterator():
            with open(safe_path, "rb") as f:
                f.seek(start)
                bytes_left = chunk_size
                while bytes_left > 0:
                    read_size = min(bytes_left, 1024 * 1024) # 1MB chunks
                    data = f.read(read_size)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data
                    
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": "video/mp4",
        }
        
        return StreamingResponse(file_iterator(), status_code=206, headers=headers)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid Range header")
