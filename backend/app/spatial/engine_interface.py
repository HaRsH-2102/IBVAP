"""
IBVAP Spatial Engine Interface
==============================
Defines the base contract for the Spatial Intelligence engine.
"""

from abc import ABC, abstractmethod
from typing import List
from app.domain.track import Track
from app.domain.spatial import SpatialEvent, CameraSpatialConfig

class BaseSpatialEngine(ABC):
    """
    Abstract Base Class for Spatial Engines.
    
    The SpatialEngine operates strictly on Track objects (M4 output) and a
    camera-specific spatial configuration. It does NOT interact with AI models
    or video frames directly.
    """
    
    @abstractmethod
    def process(self, tracks: List[Track], config: CameraSpatialConfig) -> List[SpatialEvent]:
        """
        Processes the current active tracks against the spatial configuration,
        and returns any new SpatialEvents (e.g. ZONE_ENTER, LINE_CROSS) triggered
        during this cycle.
        
        Args:
            tracks: The list of active tracks from the tracker.
            config: The geometric configuration for the current camera.
            
        Returns:
            A list of newly generated spatial events.
        """
        pass
