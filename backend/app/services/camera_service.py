"""
IBVAP Services — Camera Service
=================================
Business logic for camera management operations.

The CameraService is the single authoritative source of truth for
camera lifecycle management. All camera operations (register, configure,
enable/disable) go through this service.

NOT IMPLEMENTED in Milestone 1.
Implementation begins in Milestone 14 (when database persistence is added).
"""

from __future__ import annotations

from app.domain.camera import Camera, CameraStatus
from app.logging_config import get_logger

logger = get_logger(__name__)


class CameraService:
    """
    Manages camera registration, configuration, and lifecycle.

    Future:
        - Database-backed camera registry
        - StreamManager lifecycle management per camera
        - Camera health monitoring
        - Configuration validation
    """

    def get_all_cameras(self) -> list[Camera]:
        """
        Retrieve all registered cameras.

        NOT IMPLEMENTED — Milestone 14.
        """
        raise NotImplementedError(
            "Milestone 14: Implement camera retrieval from database. "
            "Return list of Camera objects."
        )

    def get_camera(self, camera_id: str) -> Camera:
        """
        Retrieve a specific camera by ID.

        Raises:
            ResourceNotFoundException: If camera_id does not exist.

        NOT IMPLEMENTED — Milestone 14.
        """
        raise NotImplementedError(
            "Milestone 14: Implement camera lookup by camera_id."
        )

    def register_camera(self, camera: Camera) -> Camera:
        """
        Register a new camera with the platform.

        Validates configuration, persists to database, and returns the saved Camera.

        NOT IMPLEMENTED — Milestone 14.
        """
        raise NotImplementedError(
            "Milestone 14: Implement camera registration with database persistence."
        )

    def update_camera_status(self, camera_id: str, status: CameraStatus) -> Camera:
        """
        Update the operational status of a camera.

        NOT IMPLEMENTED — Milestone 14.
        """
        raise NotImplementedError(
            "Milestone 14: Implement camera status update."
        )

    def delete_camera(self, camera_id: str) -> None:
        """
        Remove a camera registration from the platform.

        NOT IMPLEMENTED — Milestone 14.
        """
        raise NotImplementedError(
            "Milestone 14: Implement camera deletion with cascade cleanup."
        )
