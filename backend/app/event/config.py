import yaml
import logging
from typing import List

from app.domain.rule import Rule, CorrelationPolicy, Severity

logger = logging.getLogger("IBVAP.EventConfig")

def load_rules(filepath: str) -> List[Rule]:
    """
    Loads M6 rules from a YAML configuration file.
    Validates mandatory fields and returns a list of Rule objects.
    """
    rules = []
    try:
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
            
        raw_rules = data.get("rules", [])
        
        # Validation set for duplicate checks
        rule_ids = set()
        
        for r_data in raw_rules:
            r_id = r_data.get("rule_id")
            if not r_id:
                logger.error(f"Rule missing rule_id. Skipping.")
                continue
                
            if r_id in rule_ids:
                logger.error(f"Duplicate rule_id found: {r_id}. Skipping duplicate.")
                continue
            rule_ids.add(r_id)
            
            # Severity mapping
            sev_str = r_data.get("severity", "LOW")
            try:
                severity = Severity(sev_str)
            except ValueError:
                logger.error(f"Invalid severity {sev_str} for rule {r_id}. Skipping.")
                continue
                
            # Correlation Policy mapping
            cp_data = r_data.get("correlation_policy", {})
            cp = CorrelationPolicy(
                enabled=cp_data.get("enabled", True),
                window_seconds=cp_data.get("window_seconds", 5),
                matching_context=cp_data.get("matching_context", ["camera_id", "track_id"]),
                resulting_alert_policy=cp_data.get("resulting_alert_policy", "DEFAULT")
            )
            
            if cp.window_seconds <= 0:
                logger.error(f"Invalid correlation window_seconds <= 0 for rule {r_id}. Skipping.")
                continue
            
            rule = Rule(
                rule_id=r_id,
                name=r_data.get("name", r_id),
                security_event_type=r_data.get("security_event_type", "GENERIC_EVENT"),
                severity=severity,
                enabled=r_data.get("enabled", True),
                priority=r_data.get("priority", 10),
                event_type=r_data.get("event_type"),
                camera_scope=r_data.get("camera_scope"),
                spatial_object_scope=r_data.get("spatial_object_scope"),
                object_class_scope=r_data.get("object_class_scope"),
                direction_scope=r_data.get("direction_scope"),
                correlation_policy=cp
            )
            rules.append(rule)
            
        logger.info(f"Loaded {len(rules)} rules from {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to load rules from {filepath}: {e}")
        
    return rules
