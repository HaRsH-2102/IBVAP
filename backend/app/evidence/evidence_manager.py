"""
IBVAP — Evidence Management Layer (Layer 8)
============================================
EvidenceManager: Captures, stores, and manages evidence for security Events.

Evidence makes security events verifiable. Without evidence, alerts cannot
be reviewed, disputed, or used in legal/administrative proceedings.

The Evidence Manager is responsible for:
    - Capturing frame snapshots at the moment of event detection
    - Capturing short video clips around the event timestamp (optional)
    - Associating evidence with the Event
    - Managing storage and retention policy

Architectural note:
    - Evidence capture is triggered by significant events (HIGH/CRITICAL severity).
    - Evidence storage strategy (local file, object storage) is configurable.
    - Sensitive evidence (face images) requires access control in production.
    - Evidence files should NEVER be stored in the source code repository.
    - Retention is configurable — not all evidence is kept indefinitely.

NOT IMPLEMENTED in Milestone 1.
This module establishes the architectural boundary only.

Future (Milestone 13):
    - Snapshot capture from Frame.data at event timestamp
    - Short video clip capture (ring buffer approach)
    - Local filesystem evidence storage
    - Evidence metadata persistence (database)
    - Retention policy enforcement
    - Access control for evidence retrieval
"""

from __future__ import annotations

from app.domain.event import Event
from app.domain.evidence import Evidence
from app.domain.system_config import SystemConfiguration
from app.logging_config import get_logger

logger = get_logger(__name__)


class EvidenceManager:
    """
    Captures and manages evidence for security Events.

    The EvidenceManager is called by the processing pipeline when a
    significant Event is generated. It captures relevant artifacts and
    returns Evidence objects for association with the Event.

    Usage (future):
        manager = EvidenceManager(config=system_config)
        evidence_list = await manager.capture_for_event(event, frame)
    """

    def __init__(self, config: SystemConfiguration) -> None:
        self.config = config
        self._logger = get_logger("ibvap.evidence")

    def capture_snapshot(self, event: Event, frame_data: bytes, camera_id: str) -> Evidence:
        """
        Capture a frame snapshot as evidence for a security Event.

        Args:
            event: The Event this evidence belongs to.
            frame_data: Raw pixel data of the relevant frame.
            camera_id: Source camera identifier.

        Returns:
            Evidence object with type SNAPSHOT and file_reference populated.

        NOT IMPLEMENTED — Milestone 13.
        """
        raise NotImplementedError(
            "Milestone 13: Implement snapshot capture. "
            "Write frame_data to storage at config.storage_base_path. "
            "Generate unique file path using event_id + timestamp. "
            "Return Evidence with file_reference pointing to written file."
        )

    def capture_video_clip(
        self,
        event: Event,
        camera_id: str,
        duration_seconds: int = 10,
    ) -> Evidence:
        """
        Capture a short video clip around the event timestamp.

        Requires a ring buffer of recent frames (future implementation).

        NOT IMPLEMENTED — Milestone 13.
        """
        raise NotImplementedError(
            "Milestone 13: Implement video clip capture using a ring buffer "
            "of recent frames per camera. Duration should be configurable."
        )

    def enforce_retention_policy(self) -> int:
        """
        Delete evidence that has exceeded its retention period.

        Returns:
            Number of evidence items deleted.

        NOT IMPLEMENTED — Milestone 13.
        """
        raise NotImplementedError(
            "Milestone 13: Implement retention policy enforcement. "
            "Query evidence with retention_until < now() and delete storage files + database records."
        )
