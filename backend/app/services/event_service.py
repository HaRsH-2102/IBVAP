"""
IBVAP Services — Event Service
================================
Business logic for security event management.

NOT IMPLEMENTED in Milestone 1.
Implementation begins in Milestone 14.
"""

from __future__ import annotations

from app.domain.event import Event, EventStatus
from app.logging_config import get_logger

logger = get_logger(__name__)


class EventService:
    """
    Manages retrieval and lifecycle of security Events.

    Future:
        - Database-backed event storage
        - Event filtering by camera, type, severity, time range
        - Event status updates
        - Event correlation queries
    """

    def get_events(
        self,
        camera_id: str | None = None,
        limit: int = 50,
    ) -> list[Event]:
        """
        Retrieve security events, optionally filtered by camera.

        NOT IMPLEMENTED — Milestone 14.
        """
        raise NotImplementedError(
            "Milestone 14: Implement event retrieval from database with filtering."
        )

    def get_event(self, event_id: str) -> Event:
        """
        Retrieve a specific event by ID.

        Raises:
            ResourceNotFoundException: If event_id does not exist.

        NOT IMPLEMENTED — Milestone 14.
        """
        raise NotImplementedError(
            "Milestone 14: Implement event lookup by event_id."
        )

    def update_event_status(self, event_id: str, status: EventStatus) -> Event:
        """
        Update the status of a security event.

        NOT IMPLEMENTED — Milestone 14.
        """
        raise NotImplementedError(
            "Milestone 14: Implement event status update."
        )
