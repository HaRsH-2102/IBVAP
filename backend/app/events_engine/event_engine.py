"""
IBVAP — Event Engine (Layer 6)
================================
Converts spatial observations and temporal state into security Event objects.

The Event Engine is one of IBVAP's primary original contributions.
It bridges raw perception data (tracks + spatial evaluations) and
actionable security intelligence (Events).

Architectural note:
    - The EventEngine does NOT run neural networks.
    - It consumes structured Track, Zone, VirtualLine, and spatial evaluation results.
    - Each event type has its own rule logic (future: one rule class per EventType).
    - Rules should be configurable — thresholds come from SystemConfiguration,
      not hard-coded values.
    - One event processing failure must not prevent other event rules from running.

NOT IMPLEMENTED in Milestone 1.
This module establishes the architectural boundary only.

Future (Milestone 6+):
    - IntrusionRule: detects Track in RESTRICTED zone
    - LineCrossingRule: detects Track crossing VirtualLine
    - ZoneEntryRule: detects Track entering any zone
    - NightMovementRule: detects Track movement during night hours (Milestone 10)
    - LoiteringRule: detects Track in zone beyond threshold (Milestone 7)
    - ANPREventRule: creates event from PLATE detection + OCR (Milestone 8)
"""

from __future__ import annotations

from app.domain.event import Event
from app.domain.system_config import SystemConfiguration
from app.domain.track import Track
from app.domain.zone import Zone
from app.logging_config import get_logger

logger = get_logger(__name__)


class EventEngine:
    """
    Converts spatial observations into security Event objects.

    The EventEngine will contain one rule implementation per EventType.
    Rules are evaluated per frame for all active tracks.
    Rule failures are isolated — one failing rule does not stop other rules.

    Usage (future):
        engine = EventEngine(config=system_config)
        events = engine.evaluate(tracks=active_tracks, zones=camera_zones, ...)
    """

    def __init__(self, config: SystemConfiguration) -> None:
        self.config = config
        self._logger = get_logger("ibvap.events")

    def evaluate(
        self,
        tracks: list[Track],
        zones: list[Zone],
    ) -> list[Event]:
        """
        Evaluate all event rules for the current frame's track state.

        Args:
            tracks: All currently active tracks from the tracker.
            zones: Zone configurations for the current camera.

        Returns:
            List of new Event objects detected in this evaluation cycle.
            Empty list if no events were detected.

        Future rules evaluated here:
            - IntrusionRule (Milestone 6)
            - LineCrossingRule (Milestone 6)
            - ZoneEntryRule (Milestone 6)
            - LoiteringRule (Milestone 7)
            - NightMovementRule (Milestone 10)
            - ANPREventRule (Milestone 8)
            - SuspiciousActivityRules (Milestone 11)

        NOT IMPLEMENTED — Milestone 6.
        """
        raise NotImplementedError(
            "Milestone 6: Implement event evaluation rules. "
            "Each EventType should have a dedicated rule class. "
            "Rules must use config thresholds (not hard-coded values). "
            "Failures in individual rules must be caught and logged without "
            "stopping evaluation of other rules."
        )
