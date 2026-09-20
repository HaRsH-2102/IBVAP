"""
IBVAP Exception Hierarchy
==========================
All project-specific exceptions are defined here.

Design principles:
- Each architectural layer has its own exception class.
- All exceptions inherit from IBVAPBaseException for easy catch-all handling.
- Exception messages should be human-readable and include enough context to diagnose the issue.
- Do NOT catch IBVAPBaseException silently — log it with context.

Usage:
    from app.exceptions import CameraException
    raise CameraException("Camera cam-001 failed to connect", camera_id="cam-001")
"""

from __future__ import annotations


class IBVAPBaseException(Exception):
    """
    Base exception for all IBVAP-specific errors.
    Provides structured context fields for logging.
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, object] = context

    def __repr__(self) -> str:
        ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.__class__.__name__}({self.message!r}, {ctx})"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConfigurationException(IBVAPBaseException):
    """Raised when application configuration is invalid or missing."""


# ---------------------------------------------------------------------------
# Video Ingestion Layer (Layer 1)
# ---------------------------------------------------------------------------


class StreamException(IBVAPBaseException):
    """Raised when a video stream cannot be opened, read, or maintained."""


class CameraException(IBVAPBaseException):
    """Raised for camera-level errors such as connection failure or timeout."""


class FrameException(IBVAPBaseException):
    """Raised when a frame cannot be decoded or processed."""


# ---------------------------------------------------------------------------
# AI Perception Layer (Layer 3)
# ---------------------------------------------------------------------------


class PerceptionException(IBVAPBaseException):
    """
    Raised when the AI detection layer fails.
    This exception must NOT propagate beyond the camera's processing loop.
    """


class ModelLoadException(PerceptionException):
    """Raised when an AI model fails to load."""


class InferenceException(PerceptionException):
    """Raised when model inference fails on a specific frame."""


# ---------------------------------------------------------------------------
# Tracking Layer (Layer 4)
# ---------------------------------------------------------------------------


class TrackingException(IBVAPBaseException):
    """
    Raised when the tracking layer fails.
    Must not propagate beyond the camera's processing loop.
    """


# ---------------------------------------------------------------------------
# Spatial Intelligence Layer (Layer 5)
# ---------------------------------------------------------------------------


class SpatialException(IBVAPBaseException):
    """Raised for errors in zone/line evaluation logic."""


class ZoneConfigurationException(SpatialException):
    """Raised when a zone is configured with invalid geometry."""


# ---------------------------------------------------------------------------
# Event Engine (Layer 6)
# ---------------------------------------------------------------------------


class EventException(IBVAPBaseException):
    """Raised when event processing fails for a specific observation."""


# ---------------------------------------------------------------------------
# Risk Engine (Layer 7)
# ---------------------------------------------------------------------------


class RiskException(IBVAPBaseException):
    """Raised when risk assessment fails for an event."""


# ---------------------------------------------------------------------------
# Evidence Management (Layer 8)
# ---------------------------------------------------------------------------


class EvidenceException(IBVAPBaseException):
    """Raised when evidence capture or storage fails."""


class EvidenceStorageException(EvidenceException):
    """Raised when evidence cannot be written to storage."""


# ---------------------------------------------------------------------------
# Persistence Layer (Layer 9)
# ---------------------------------------------------------------------------


class PersistenceException(IBVAPBaseException):
    """Raised for database read/write failures."""


class DatabaseConnectionException(PersistenceException):
    """Raised when the database connection cannot be established."""


# ---------------------------------------------------------------------------
# API Layer (Layer 10)
# ---------------------------------------------------------------------------


class APIException(IBVAPBaseException):
    """Raised for API-level errors such as validation failures."""


class ResourceNotFoundException(APIException):
    """Raised when a requested resource does not exist."""


class PermissionDeniedException(APIException):
    """Raised when an action is not permitted for the current context."""
