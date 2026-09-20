"""
IBVAP Structured Logging Configuration
=======================================
Sets up application-wide structured logging.

Each layer gets its own named logger so log output can be filtered by component.

Logger hierarchy:
    ibvap                   Root application logger
    ibvap.api               REST API layer
    ibvap.ingestion         Video ingestion layer
    ibvap.perception        AI perception layer
    ibvap.tracking          Tracking layer
    ibvap.spatial           Spatial intelligence
    ibvap.events            Event engine
    ibvap.risk              Risk engine
    ibvap.evidence          Evidence management
    ibvap.services          Business services
    ibvap.config            Configuration subsystem
    ibvap.websocket         WebSocket layer

Usage:
    from app.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Camera %s connected", camera_id, extra={"camera_id": camera_id})
"""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure application-wide structured logging.
    Call this once at application startup (in main.py lifespan).
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # --- JSON formatter for structured output ---
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )

    # --- Console handler ---
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(numeric_level)

    # --- Root IBVAP logger ---
    root_logger = logging.getLogger("ibvap")
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(handler)
    root_logger.propagate = False  # Don't propagate to root Python logger

    # Silence noisy third-party loggers in production
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

    root_logger.info(
        "IBVAP logging initialized",
        extra={"log_level": log_level},
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a named child logger under the 'ibvap' hierarchy.

    If the provided name starts with 'app.', it is mapped to 'ibvap.<rest>'.
    This allows usage like: get_logger(__name__) in any app module.

    Args:
        name: Module name or explicit logger name.

    Returns:
        A Logger instance under the ibvap hierarchy.
    """
    if name.startswith("app."):
        # Convert 'app.ingestion.stream_manager' → 'ibvap.ingestion.stream_manager'
        child_name = name[len("app."):]
        logger_name = f"ibvap.{child_name}"
    elif not name.startswith("ibvap"):
        logger_name = f"ibvap.{name}"
    else:
        logger_name = name

    return logging.getLogger(logger_name)
