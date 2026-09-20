"""
IBVAP — Risk Engine (Layer 7)
================================
Assigns severity and risk scores to security Events.

The Risk Engine evaluates security Events using configurable rules that combine
multiple contextual factors into a severity assessment with an explanation.

The key principle is explainability — the risk engine must always produce a
human-readable explanation of why a particular risk level was assigned (Rule 8).

Architectural note:
    - The RiskEngine is separated from the EventEngine to allow independent tuning
      of scoring logic (thresholds, weights, factor combinations).
    - The rule_version field on RiskAssessment supports future A/B testing.
    - The exact scoring formula will be designed experimentally in Milestone 12.
    - Risk scores are 0.0–100.0 with configurable severity thresholds.

NOT IMPLEMENTED in Milestone 1.
This module establishes the architectural boundary only.

Future (Milestone 12):
    - Factor-based scoring: each factor adds or multiplies risk score
    - Configurable factor weights
    - Compound risk from correlated events (same track + multiple events)
    - Temporal decay (recent events weigh more than old ones)
    - Example factors: night_time, restricted_zone, extended_dwell, vehicle_class,
      repeated_violation, proximity_to_critical_asset
"""

from __future__ import annotations

from app.domain.event import Event
from app.domain.risk_assessment import RiskAssessment
from app.domain.system_config import SystemConfiguration
from app.logging_config import get_logger

logger = get_logger(__name__)


class RiskEngine:
    """
    Assigns risk scores and severity levels to security Events.

    Produces RiskAssessment objects that explain the severity determination
    in both machine-readable (contributing_factors) and human-readable (explanation)
    formats.

    Usage (future):
        engine = RiskEngine(config=system_config)
        assessment = engine.assess(event)
    """

    def __init__(self, config: SystemConfiguration) -> None:
        self.config = config
        self._logger = get_logger("ibvap.risk")

    def assess(self, event: Event) -> RiskAssessment:
        """
        Evaluate the risk of a security Event and produce a RiskAssessment.

        The assessment combines:
            - Event type base severity
            - Contextual modifiers (time of day, zone type, dwell duration, etc.)
            - Object class modifiers (vehicle vs person)
            - History modifiers (repeated violations from same track)

        Args:
            event: The security Event to assess.

        Returns:
            RiskAssessment with risk_score, severity, contributing_factors,
            and human-readable explanation.

        NOT IMPLEMENTED — Milestone 12.
        """
        raise NotImplementedError(
            "Milestone 12: Implement risk scoring logic. "
            "Design should combine: event type base score + contextual modifiers. "
            "contributing_factors must be a machine-readable list. "
            "explanation must be human-readable. "
            "Scoring weights should be configurable, not hard-coded."
        )
