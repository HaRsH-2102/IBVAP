"""
IBVAP Domain — SeverityLevel
==============================
Shared severity enum used by Event, RiskAssessment, and Alert.

Defined in a separate shared module to avoid circular imports between
event.py, risk_assessment.py, and alert.py.
"""

from __future__ import annotations

from enum import Enum


class SeverityLevel(str, Enum):
    """
    Security severity classification used across events, risk assessments, and alerts.

    Progression: LOW < MEDIUM < HIGH < CRITICAL

    Semantics:
        LOW:      Informational. May not require immediate action.
        MEDIUM:   Notable activity. Operator should review.
        HIGH:     Significant security concern. Prompt attention required.
        CRITICAL: Immediate threat. Operator must respond now.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
