"""
IBVAP Domain — RiskAssessment
==============================
Represents the security significance evaluation of an Event.

The RiskEngine (Layer 7) produces a RiskAssessment for each significant Event.
The assessment combines multiple contextual factors into a severity score and
provides a human-readable explanation.

Architectural note:
    - The RiskEngine is separated from the EventEngine to allow independent
      tuning of scoring logic without modifying event detection logic.
    - The rule_version field supports future A/B testing of scoring strategies.
    - The contributing_factors list supports Rule 8 (Explainable Alerts) —
      operators should always understand why a HIGH/CRITICAL alert was generated.
    - Risk scores are advisory — the final severity can be overridden by operators.

Future (Milestone 12+):
    - Configurable rule sets per zone/camera
    - Temporal weighting (repeated violations increase score)
    - Cross-event correlation (combine multiple events for compound risk)
    - ML-based risk calibration after initial rule-based implementation
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.severity import SeverityLevel


class RiskAssessment(BaseModel):
    """
    The security significance evaluation of an Event.

    Produced by the RiskEngine (Layer 7) to quantify and explain the threat
    level of a detected security Event.

    The assessment must be explainable — contributing_factors and explanation
    are mandatory for HIGH and CRITICAL severity assessments.

    Attributes:
        assessment_id: Unique identifier.
        event_id: The Event this assessment applies to.
        risk_score: Numeric risk score in range [0.0, 100.0].
            (0 = no risk, 100 = maximum severity)
        severity: Severity level derived from risk_score and rule logic.
        contributing_factors: Machine-readable list of factors that increased
            the risk score. Examples: "night_time", "restricted_zone",
            "extended_dwell", "repeated_violation", "vehicle_class:truck".
        explanation: Human-readable explanation of why this risk level was assigned.
        rule_version: Identifier of the risk rule set version used.
            Enables audit trail and future rule comparison.

    Future:
        - confidence_in_assessment: RiskEngine's own confidence
        - recommended_response: suggested operator action
        - escalation_trigger: bool (if True, escalate to supervisor)
    """

    assessment_id: str = Field(..., description="Unique assessment identifier (UUID)")
    event_id: str = Field(..., description="The Event this assessment evaluates")
    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Numeric risk score [0.0, 100.0]",
    )
    severity: SeverityLevel = Field(
        default=SeverityLevel.LOW,
        description="Severity level derived from risk_score",
    )
    contributing_factors: list[str] = Field(
        default_factory=list,
        description="Machine-readable factors that influenced the risk score",
    )
    explanation: str = Field(
        default="",
        description="Human-readable explanation of the risk assessment",
    )
    rule_version: str = Field(
        default="undefined",
        description="Version identifier of the risk rule set used",
    )


# Re-export SeverityLevel for convenience
__all__ = ["RiskAssessment", "SeverityLevel"]
