"""
IBVAP Backend — FastAPI Application Entry Point
================================================
This is the main application file. It creates the FastAPI app, registers
all routers, configures middleware, and manages application lifecycle.

Usage:
    uvicorn app.main:app --reload

API Documentation:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import asyncio
from app.api.routers import (
    system,
    cameras,
    events,
    alerts,
    zones,
    artifacts,
    anpr,
    validation,
    videos,
    analytics,
)
from app.api.websocket import router as ws_router, periodic_track_updates
from app.config import settings
from app.logging_config import configure_logging, get_logger
import os

async def evidence_cleanup_worker():
    from app.infrastructure.database import SQLiteDatabase
    from app.infrastructure.repositories import EvidenceRepository
    db = SQLiteDatabase()
    repo = EvidenceRepository(db)
    logger = get_logger("ibvap.cleanup")
    
    while True:
        try:
            expired_list = repo.get_expired_evidence()
            for ev in expired_list:
                # 1. Delete Crop
                if ev.crop_path and os.path.exists(ev.crop_path):
                    os.remove(ev.crop_path)
                # 2. Delete Full
                if ev.full_frame_path and os.path.exists(ev.full_frame_path):
                    os.remove(ev.full_frame_path)
                # 3. Delete DB record
                repo.delete(ev.evidence_id)
                logger.info(f"Evidence cleanup: {ev.event_id} expired. crop deleted, full frame deleted, database record deleted.")
        except Exception as e:
            logger.error(f"Evidence cleanup failed: {e}")
        await asyncio.sleep(60) # check every minute

@asynccontextmanager

async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """
    Application lifespan manager.
    Code before 'yield' runs on startup; code after runs on shutdown.
    """
    # --- Startup ---
    configure_logging(settings.log_level)
    logger = get_logger("ibvap.main")

    logger.info(
        "IBVAP Backend starting",
        extra={
            "milestone": 1,
            "api_version": settings.api_version,
            "log_level": settings.log_level,
        },
    )
    logger.info(
        "Milestone 1: Foundation & Architecture. "
        "Video ingestion, AI inference, and dashboard are NOT yet active."
    )

    # Start WS background task
    bg_task = asyncio.create_task(periodic_track_updates())
    cleanup_task = asyncio.create_task(evidence_cleanup_worker())

    yield  # Application runs here

    bg_task.cancel()
    cleanup_task.cancel()

    # --- Shutdown ---
    logger.info("IBVAP Backend shutting down")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="IBVAP — Intelligent Border Video Analytics Platform",
    description=(
        "**SIH26187** — Software-defined surveillance intelligence platform.\n\n"
        "**Current Status:** Milestone 1 — Foundation & Architecture.\n\n"
        "Most endpoints return `501 Not Implemented` — they are architectural "
        "placeholders for future milestones. See `/api/v1/system/status` for "
        "the capability roadmap.\n\n"
        "**Implemented in Milestone 1:**\n"
        "- Domain model contracts\n"
        "- Configuration system\n"
        "- Structured logging\n"
        "- API boundaries\n"
        "- WebSocket boundary (`/ws`)\n"
        "- System health endpoints\n"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------

API_PREFIX = f"/api/{settings.api_version}"

app.include_router(system.router, prefix=API_PREFIX)
app.include_router(cameras.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)
app.include_router(alerts.router, prefix=API_PREFIX)
app.include_router(zones.router, prefix=API_PREFIX)
app.include_router(artifacts.router, prefix=API_PREFIX)
app.include_router(anpr.router, prefix=API_PREFIX)
app.include_router(validation.router, prefix=API_PREFIX)
app.include_router(videos.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(ws_router)  # WebSocket at /ws (no API prefix)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Root redirect information."""
    return {
        "service": "IBVAP Backend",
        "milestone": 1,
        "docs": "/docs",
        "health": f"{API_PREFIX}/system/health",
        "status": f"{API_PREFIX}/system/status",
        "websocket": "/ws",
    }
