import os
import time
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from app.services.validation_runner import runner

router = APIRouter(prefix="/validation", tags=["validation"])

class StartRequest(BaseModel):
    video_id: str

class ReviewRequest(BaseModel):
    decision: str

@router.post("/start")
async def start_validation(req: StartRequest):
    loop = asyncio.get_event_loop()
    try:
        session_id = runner.start_session(req.video_id, loop)
        return {"status": "started", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def get_validation_status():
    return {
        "is_running": runner.is_running,
        "session_id": runner.session_id,
        "video_id": runner.video_id if hasattr(runner, 'video_id') else None
    }

@router.post("/stop")
async def stop_validation():
    runner.stop_session()
    return {"status": "stopped"}

@router.post("/review/{event_id}")
async def review_event(event_id: str, req: ReviewRequest):
    runner.record_decision(event_id, req.decision)
    return {"status": "recorded"}

@router.post("/pause")
async def pause_validation():
    runner.pause()
    return {"status": "paused"}

@router.post("/play")
async def resume_validation():
    runner.resume()
    return {"status": "resumed"}

class SpeedRequest(BaseModel):
    speed: float

class SeekRequest(BaseModel):
    timestamp_sec: float

@router.post("/pause")
async def pause_video():
    runner.pause()
    return {"status": "paused"}

@router.post("/play")
async def play_video():
    runner.resume()
    return {"status": "playing"}

@router.post("/speed")
async def set_speed(req: SpeedRequest):
    runner.set_speed(req.speed)
    return {"status": "speed_set", "speed": req.speed}

@router.post("/seek")
async def seek_video(req: SeekRequest):
    runner.seek(req.timestamp_sec)
    return {"status": "seek_triggered", "timestamp": req.timestamp_sec}

@router.get("/evidence/{event_type}/{filename}")
async def get_evidence(event_type: str, filename: str):
    # E.g. results/evidence/LOITERING/some_event_crop.jpg
    evidence_root = os.path.abspath(os.path.join("results", "evidence"))
    path = os.path.join(evidence_root, event_type, filename)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Evidence not found")

@router.post("/evidence/{event_id}/save")
async def save_evidence(event_id: str):
    from app.infrastructure.database import SQLiteDatabase
    from app.infrastructure.repositories import EvidenceRepository
    db = SQLiteDatabase()
    repo = EvidenceRepository(db)
    ev = repo.get_by_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    repo.save_status(ev.evidence_id, True)
    
    # Return updated state
    updated_ev = repo.get_by_event(event_id)
    return {"status": "saved", "is_saved": True, "saved_at": updated_ev.saved_at.isoformat()}

@router.post("/evidence/{event_id}/delete")
async def delete_evidence(event_id: str):
    from app.infrastructure.database import SQLiteDatabase
    from app.infrastructure.repositories import EvidenceRepository
    db = SQLiteDatabase()
    repo = EvidenceRepository(db)
    ev = repo.get_by_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
        
    # Delete files
    if ev.crop_path and os.path.exists(ev.crop_path):
        os.remove(ev.crop_path)
    if ev.full_frame_path and os.path.exists(ev.full_frame_path):
        os.remove(ev.full_frame_path)
        
    # Delete DB
    repo.delete(ev.evidence_id)
    
    return {"status": "deleted"}

@router.get("/evidence/{event_id}/info")
async def get_evidence_info(event_id: str):
    from app.infrastructure.database import SQLiteDatabase
    from app.infrastructure.repositories import EvidenceRepository
    db = SQLiteDatabase()
    repo = EvidenceRepository(db)
    ev = repo.get_by_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {
        "evidence_id": ev.evidence_id,
        "event_id": ev.event_id,
        "is_saved": ev.is_saved,
        "expires_at": ev.expires_at.isoformat() if ev.expires_at else None,
        "saved_at": ev.saved_at.isoformat() if ev.saved_at else None
    }


def frame_generator():
    while True:
        if runner.is_running:
            frame = runner.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.01)
            else:
                time.sleep(0.01)
        else:
            time.sleep(0.5)

@router.get("/stream")
async def stream_video():
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
