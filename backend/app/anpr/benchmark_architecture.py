"""
IBVAP ANPR — Event-Driven Benchmark Architecture
================================================

Implements the strictly event-driven gating for ANPR benchmarking.
ANPR must only run if a valid SecurityEvent for a vehicle exists.
"""

from typing import Optional, Dict
from dataclasses import dataclass
import asyncio
import logging

from app.domain.security import SecurityEvent, EvidencePackage

logger = logging.getLogger("ibvap.anpr.benchmark")

# 1. Class Normalization Mapping
# Maps raw detector classes to normalized vehicle categories.
RTDETR_CLASS_MAPPING = {
    "car": "CAR",
    "truck": "TRUCK",
    "bus": "BUS",
    "motorcycle": "MOTORCYCLE",
    "bicycle": "BIKE",
    # Add any other detector-specific labels here that map to standard vehicles
}

VALID_ANPR_VEHICLES = {"CAR", "BIKE", "MOTORCYCLE", "TRUCK", "BUS"}

def normalize_vehicle_class(raw_class: str) -> Optional[str]:
    """Returns normalized vehicle class or None if not a supported vehicle."""
    if not raw_class:
        return None
    raw_lower = str(raw_class).lower()
    return RTDETR_CLASS_MAPPING.get(raw_lower)

def is_anpr_eligible(event: Optional[SecurityEvent], evidence: Optional[EvidencePackage]) -> bool:
    """
    The Single Source of Truth for ANPR eligibility.
    Conditions:
    1. Event must exist and be registered (status != FAILED/REJECTED).
    2. Evidence must exist and have a valid crop.
    3. The object MUST NOT be a person.
    4. The normalized class must be a valid vehicle.
    """
    # Reject if missing event or evidence
    if not event or not evidence:
        return False

    # For the benchmark, we expect standard events to have status "PROCESSED" or "REGISTERED"
    # But essentially it must be a valid registered event.
    if event.status in ["FAILED", "REJECTED", "INVALID"]:
        return False

    raw_class = evidence.object_class.lower()

    # Reject PERSON explicitly
    if raw_class == "person":
        return False

    # Normalize class
    normalized = normalize_vehicle_class(raw_class)
    
    if not normalized or normalized not in VALID_ANPR_VEHICLES:
        return False

    # Must have evidence crop
    if not evidence.crop_path:
        return False

    return True


class ANPRBenchmarkQueue:
    """
    Asynchronous Queue to decouple ANPR processing from the event pipeline.
    Maintains strict event_id deduplication.
    """
    def __init__(self):
        self.queue = asyncio.Queue()
        self.processed_events = set()
        self._logger = logging.getLogger("ibvap.anpr.queue")

    def submit_event(self, event: SecurityEvent, evidence: EvidencePackage) -> bool:
        """
        Attempts to submit an event to the ANPR queue.
        Returns True if queued, False if rejected (ineligible or duplicate).
        """
        # Deduplication Check
        if event.event_id in self.processed_events:
            self._logger.debug(f"Event {event.event_id} already processed for ANPR. Skipping duplicate.")
            return False

        # Eligibility Check
        if not is_anpr_eligible(event, evidence):
            self._logger.debug(f"Event {event.event_id} failed ANPR eligibility filter.")
            return False

        # Accept
        self.processed_events.add(event.event_id)
        # Put non-blocking (asyncio queue requires no await if using put_nowait)
        try:
            self.queue.put_nowait((event, evidence))
            self._logger.info(f"Event {event.event_id} queued for ANPR.")
            return True
        except asyncio.QueueFull:
            self._logger.error(f"ANPR Queue full, dropped event {event.event_id}")
            return False

    async def get_job(self) -> tuple[SecurityEvent, EvidencePackage]:
        """Waits and retrieves the next ANPR job."""
        return await self.queue.get()

    def mark_done(self):
        """Marks the current job as done in the queue."""
        self.queue.task_done()
