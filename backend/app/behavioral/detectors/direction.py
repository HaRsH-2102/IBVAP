import math
from typing import List
from datetime import datetime
from app.domain.behavioral import BehavioralEvent, BehavioralEventType
from app.behavioral.track_state import TrackBehavioralState
from app.behavioral.config import BehavioralConfig
from app.behavioral.detectors.base import BehaviorDetector

def calculate_angle(p1, p2):
    return math.degrees(math.atan2(p2.y - p1.y, p2.x - p1.x))

class DirectionDetector(BehaviorDetector):
    def detect(self, state: TrackBehavioralState, config: BehavioralConfig, timestamp: datetime) -> List[BehavioralEvent]:
        events = []
        
        b_state = state.active_behaviors.setdefault("DIRECTION", {
            "last_reversal_time": None,
            "last_angle": None,
            "last_reversal_point": None,
            "original_point": None
        })
        
        # We need enough history to calculate a smoothed vector
        if len(state.history) < config.jitter_smoothing_window * 2 + 1:
            return events
            
        # Get recent points
        history = list(state.history)
        w = config.jitter_smoothing_window
        
        p_old = history[-(2 * w + 1)].point
        p_mid = history[-(w + 1)].point
        p_new = history[-1].point
        
        dist1 = math.hypot(p_mid.x - p_old.x, p_mid.y - p_old.y)
        dist2 = math.hypot(p_new.x - p_mid.x, p_new.y - p_mid.y)
        
        # Minimum displacement to consider it a meaningful movement rather than jitter
        min_disp = 10.0
        
        if dist1 > min_disp and dist2 > min_disp:
            angle1 = calculate_angle(p_old, p_mid)
            angle2 = calculate_angle(p_mid, p_new)
            
            # Angle difference
            diff = abs(angle1 - angle2)
            if diff > 180:
                diff = 360 - diff
                
            if diff >= config.direction_change_threshold_degrees:
                # Meaningful reversal
                last_rev = b_state["last_reversal_time"]
                
                # Prevent spamming reversals
                if not last_rev or (timestamp - last_rev).total_seconds() > 5.0:
                    b_state["last_reversal_time"] = timestamp
                    b_state["last_reversal_point"] = p_mid
                    b_state["original_point"] = p_old
                    
                    evidence = {
                        "angle_change": diff,
                        "threshold": config.direction_change_threshold_degrees
                    }
                    
                    event = self._create_event(
                        state, BehavioralEventType.DIRECTION_REVERSAL, 
                        history[-w].timestamp, timestamp, 
                        (timestamp - history[-w].timestamp).total_seconds(), evidence
                    )
                    event.end_time = timestamp
                    events.append(event)
                    
        # Check for rapid backtrack
        if b_state["last_reversal_time"]:
            elapsed = (timestamp - b_state["last_reversal_time"]).total_seconds()
            if elapsed <= config.backtrack_window:
                orig_pt = b_state["original_point"]
                if orig_pt:
                    # Are we close to the original point?
                    dist_to_orig = math.hypot(p_new.x - orig_pt.x, p_new.y - orig_pt.y)
                    if dist_to_orig < min_disp * 2:
                        # We are back!
                        evidence = {
                            "backtrack_time": elapsed,
                            "window": config.backtrack_window
                        }
                        event = self._create_event(
                            state, BehavioralEventType.RAPID_BACKTRACK, 
                            b_state["last_reversal_time"], timestamp, elapsed, evidence
                        )
                        event.end_time = timestamp
                        events.append(event)
                        
                        # Clear to prevent spam
                        b_state["last_reversal_time"] = None
            else:
                # Window expired
                b_state["last_reversal_time"] = None
                
        return events
