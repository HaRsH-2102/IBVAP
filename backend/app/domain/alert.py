"""
IBVAP Domain — Alert
=====================
Represents an operator-facing notification requiring attention or action.

An Alert is the highest-level output of the IBVAP system visible to operators.
Not all Events generate Alerts — only Events above a configured severity threshold,
or Events matching specific configured conditions, produce Alerts.

Architectural note:
    - Alerts are produced by the AlertService based on Event + RiskAssessment.
    - The alert lifecycle models real security operations center (SOC) workflow.
    - Alert state transitions must be logged for audit purposes.
    - Alert acknowledgement/resolution times are important KPIs for the operator.

Future (Milestone 14+):
    - Database persistence
    - Escalation rules (alert not acknowledged within N minutes → escalate)
    - Role-based alert routing (different operators see different camera alerts)
    - Alert suppression rules (prevent duplicate alerts for same ongoing event)
    - Audit log per state transition
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.domain.severity import SeverityLevel


class AlertState(str, Enum):
    """
    Lifecycle states of an Alert.

    Transitions:
        DETECTED → ACTIVE → ACKNOWLEDGED → INVESTIGATING → RESOLVED

    Operators can also suppress alerts to prevent repeated notifications.
    """

    DETECTED = "DETECTED"           # Alert has been generated, not yet pushed to operator
    ACTIVE = "ACTIVE"               # Alert is live and visible to operator
    ACKNOWLEDGED = "ACKNOWLEDGED"   # Operator has seen the alert
    INVESTIGATING = "INVESTIGATING" # Operator is actively investigating
    RESOLVED = "RESOLVED"           # Alert has been closed with resolution
    SUPPRESSED = "SUPPRESSED"       # Alert suppressed (duplicate, false positive, etc.)


class Alert(BaseModel):
    """
    Represents an operator-facing security notification.

    Alerts are the highest-level actionable output of IBVAP.
    Their lifecycle tracks the security operations center (SOC) workflow
    from detection through to resolution.

    Attributes:
        alert_id: Unique identifier.
        event_id: The Event that triggered this alert.
        severity: Inherited from the Event/RiskAssessment at time of creation.
        state: Current lifecycle state.
        created_at: UTC time when the alert was generated.
        acknowledged_at: UTC time when the operator acknowledged the alert.
        resolved_at: UTC time when the alert was closed.
        operator_id: ID of the operator who acknowledged/resolved this alert.
        notes: Free-text operator notes about this alert (for audit trail).

    Future:
        - escalation_at: Time at which the alert should be escalated
        - escalated_to: Operator or role to escalate to
        - resolution_category: Enum (TRUE_POSITIVE, FALSE_POSITIVE, INCONCLUSIVE)
        - response_time_seconds: computed KPI metric
    """

    alert_id: str = Field(..., description="Unique alert identifier (UUID)")
    event_id: str = Field(..., description="The Event that triggered this alert")
    severity: SeverityLevel = Field(..., description="Alert severity level")
    state: AlertState = Field(default=AlertState.DETECTED)
    created_at: datetime = Field(..., description="UTC time of alert generation")
    acknowledged_at: datetime | None = Field(default=None, description="UTC time of acknowledgement")
    resolved_at: datetime | None = Field(default=None, description="UTC time of resolution")
    operator_id: str | None = Field(default=None, description="ID of operator who acted on this alert")
    notes: str | None = Field(default=None, description="Operator notes for audit trail")
