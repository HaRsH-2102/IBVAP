import cv2
import numpy as np
from typing import Dict, Any, Optional

class EvidenceRenderer:
    """
    Renders visual overlays for evidence frames.
    Non-destructive: Always creates a copy of the original frame.
    """
    
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.thickness = 2
        self.text_color = (0, 255, 255) # Yellow
        self.bg_color = (0, 0, 0)
        self.box_color = (0, 0, 255) # Red for evidence box
        
    def _draw_text_with_bg(self, img: np.ndarray, text: str, pos: tuple[int, int]):
        (w, h), baseline = cv2.getTextSize(text, self.font, self.font_scale, self.thickness)
        x, y = pos
        # Draw background rect
        cv2.rectangle(img, (x, y - h - 5), (x + w, y + baseline), self.bg_color, -1)
        # Draw text
        cv2.putText(img, text, (x, y), self.font, self.font_scale, self.text_color, self.thickness)

    def render(
        self, 
        original_frame: np.ndarray, 
        bounding_box: Optional[Dict[str, int]], 
        event_type: str,
        track_id: Optional[str],
        object_class: Optional[str],
        timestamp_str: str,
        camera_id: str,
        spatial_context: Optional[Dict[str, Any]] = None,
        behavioral_context: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Takes the original immutable frame, copies it, and draws the requested metadata.
        """
        # 1. Non-destructive copy
        frame = original_frame.copy()
        
        # 2. Draw Bounding Box if present
        if bounding_box:
            x1, y1 = bounding_box.get('x1', 0), bounding_box.get('y1', 0)
            x2, y2 = bounding_box.get('x2', 0), bounding_box.get('y2', 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.box_color, 2)
            
            # Label above bounding box
            label = f"{object_class or 'Unknown'} {track_id or ''}".strip()
            if label:
                self._draw_text_with_bg(frame, label, (x1, max(20, y1 - 10)))
                
        # 3. Draw Event Information Block (Top Left)
        info_lines = [
            f"EVIDENCE: {event_type}",
            f"CAM: {camera_id}",
            f"TIME: {timestamp_str}"
        ]
        
        if spatial_context:
            if 'zone_id' in spatial_context:
                info_lines.append(f"ZONE: {spatial_context['zone_id']}")
            if 'line_id' in spatial_context:
                info_lines.append(f"LINE: {spatial_context['line_id']}")
                
        if behavioral_context:
            if 'dwell_seconds' in behavioral_context:
                info_lines.append(f"DWELL: {behavioral_context['dwell_seconds']:.1f}s")
                
        start_y = 30
        for i, line in enumerate(info_lines):
            self._draw_text_with_bg(frame, line, (10, start_y + (i * 30)))
            
        return frame
