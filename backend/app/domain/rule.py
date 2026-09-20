from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum

class Severity(Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertStatus(Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

@dataclass
class CorrelationPolicy:
    enabled: bool = True
    window_seconds: int = 5
    matching_context: List[str] = field(default_factory=lambda: ["camera_id", "track_id"])
    resulting_alert_policy: str = "DEFAULT"

@dataclass
class Rule:
    rule_id: str
    name: str
    security_event_type: str
    severity: Severity
    enabled: bool = True
    priority: int = 10
    description: str = ""
    
    # Scopes/Constraints
    event_type: Optional[List[str]] = None
    camera_scope: Optional[List[str]] = None
    spatial_object_scope: Optional[List[str]] = None
    object_class_scope: Optional[List[str]] = None
    direction_scope: Optional[List[str]] = None
    
    # Policies
    alert_policy: str = "DEFAULT"
    correlation_policy: Optional[CorrelationPolicy] = None

    def __post_init__(self):
        if self.correlation_policy is None:
            self.correlation_policy = CorrelationPolicy()
