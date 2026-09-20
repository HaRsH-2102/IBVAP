from dataclasses import dataclass

@dataclass
class BehavioralConfig:
    # Loitering
    loitering_duration: float = 10.0
    loitering_radius: float = 50.0
    loitering_reset_duration: float = 3.0

    # Stationary
    stationary_duration: float = 30.0
    stationary_radius: float = 15.0

    # Restricted Zone Dwell
    restricted_zone_dwell_duration: float = 30.0

    # Repeated Zone Entry
    repeated_zone_entry_count: int = 3
    repeated_zone_entry_window: float = 60.0

    # Boundary Approach
    boundary_approach_count: int = 3
    boundary_approach_window: float = 60.0

    # Direction Reversal & Rapid Backtrack
    direction_change_threshold_degrees: float = 90.0
    backtrack_window: float = 10.0
    
    # State keeping constraints
    max_history_points: int = 300
    jitter_smoothing_window: int = 5
