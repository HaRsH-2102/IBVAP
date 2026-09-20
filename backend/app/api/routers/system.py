"""
IBVAP API — System Router
===========================
Provides health checks and system status endpoints.

These endpoints are IMPLEMENTED in Milestone 1 (unlike other routers).
They are essential for validating that the backend is running and configured correctly.

Endpoints:
    GET /api/v1/system/health   — Liveness check
    GET /api/v1/system/status   — System readiness and configuration summary
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings
from app.domain.system_config import SystemConfiguration

router = APIRouter(prefix="/system", tags=["system"])

# Track service start time for uptime reporting
_start_time = datetime.now(timezone.utc)


@router.get("/health", summary="Health check")
async def health_check() -> dict:
    """
    Liveness probe endpoint.

    Returns a simple OK response to confirm the backend process is running.
    Use this for load balancer health checks and Docker HEALTHCHECK.
    """
    return {
        "status": "ok",
        "service": "IBVAP Backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status", summary="System status and configuration")
async def system_status() -> dict:
    """
    Returns system readiness status and current configuration summary.

    This endpoint is safe to expose to operators — it does NOT include
    sensitive configuration values (credentials, database URLs, etc.).
    """
    config = SystemConfiguration.from_settings(settings)
    uptime_seconds = (datetime.now(timezone.utc) - _start_time).total_seconds()

    return {
        "status": "foundation_ready",
        "milestone": 1,
        "description": "IBVAP Milestone 1 — Foundation & Architecture established. "
                        "AI inference, video ingestion, and dashboard are not yet implemented.",
        "uptime_seconds": round(uptime_seconds, 1),
        "configuration": config.model_dump(),
        "capabilities": {
            "video_ingestion": {"status": "not_implemented", "milestone": 2},
            "object_detection": {"status": "not_implemented", "milestone": 3},
            "object_tracking": {"status": "not_implemented", "milestone": 4},
            "spatial_intelligence": {"status": "not_implemented", "milestone": 5},
            "event_engine": {"status": "not_implemented", "milestone": 6},
            "risk_engine": {"status": "not_implemented", "milestone": 12},
            "evidence_management": {"status": "not_implemented", "milestone": 13},
            "persistence": {"status": "not_implemented", "milestone": 14},
            "dashboard": {"status": "not_implemented", "milestone": 15},
        },
    }


@router.get("/metrics", summary="System resource metrics")
async def system_metrics() -> dict:
    """
    Returns current system resource usage: CPU, memory, disk, and GPU (if available).
    Used by the frontend System Health dashboard.
    """
    import psutil
    import os

    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()

    # Memory
    mem = psutil.virtual_memory()
    memory = {
        "total_gb": round(mem.total / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "percent": mem.percent,
    }

    # Disk (storage path)
    storage_path = settings.storage_base_path
    try:
        disk = psutil.disk_usage(storage_path if os.path.exists(storage_path) else "/")
        disk_info = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent,
        }
    except Exception:
        disk_info = {"error": "Unable to read disk usage"}

    # GPU (optional)
    gpu_info = []
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            gpu_info.append({
                "id": gpu.id,
                "name": gpu.name,
                "load_percent": round(gpu.load * 100, 1),
                "memory_total_mb": round(gpu.memoryTotal, 0),
                "memory_used_mb": round(gpu.memoryUsed, 0),
                "memory_free_mb": round(gpu.memoryFree, 0),
                "memory_percent": round(gpu.memoryUtil * 100, 1) if gpu.memoryUtil else 0,
                "temperature_c": gpu.temperature,
            })
    except ImportError:
        gpu_info = [{"status": "GPUtil not installed"}]
    except Exception as e:
        gpu_info = [{"status": f"GPU query failed: {str(e)}"}]

    uptime_seconds = (datetime.now(timezone.utc) - _start_time).total_seconds()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(uptime_seconds, 1),
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count,
        },
        "memory": memory,
        "disk": disk_info,
        "gpu": gpu_info,
    }
