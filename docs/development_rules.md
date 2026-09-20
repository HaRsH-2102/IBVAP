# IBVAP — Engineering Rules

**These rules apply to every milestone and every contributor.**

---

## Rule 1 — No Fake AI

Never simulate AI output and present it as real.

A function that returns hard-coded bounding boxes and calls them "detections" is a lie.  
A dashboard that shows "3 people detected" from random numbers is misleading.

If something is not implemented, return a clear `not_implemented` response.  
If a capability is planned for a future milestone, document it as such.

---

## Rule 2 — Modular AI

All AI models must be replaceable without rewriting the surrounding system.

- Object detectors implement `BaseDetector`
- Trackers implement `BaseTracker`
- OCR engines are accessed through a common interface
- Face detectors are isolated from the rest of the pipeline

If you find yourself writing `from ultralytics import YOLO` in the event engine, you have broken this rule.

---

## Rule 3 — Measure Before Optimizing

Do not add TensorRT, ONNX export, NVIDIA DeepStream, or batch inference optimizations without a measured bottleneck.

Premature optimization adds complexity without confirmed benefit.  
After the correct working pipeline exists, measure FPS, GPU utilization, and latency — then optimize.

---

## Rule 4 — One Milestone at a Time

Do not implement future milestones without explicit approval.

If you are working on Milestone 3 (detection) and you start implementing tracking (Milestone 4), stop.  
Each milestone is reviewed and validated before the next begins.

---

## Rule 5 — Test Every Milestone

A milestone is not complete because the code runs once.

Each milestone must include:
- Unit tests for domain logic
- Integration tests for API endpoints
- At minimum one end-to-end validation of the milestone's primary capability

---

## Rule 6 — Keep Security in Mind

- No credentials in source code
- No secrets committed to git
- Camera stream URLs and passwords go in `.env` (never in `config.py` defaults)
- Face imagery is sensitive — minimize storage and access
- Evidence files require access control in future versions
- API inputs must be validated

---

## Rule 7 — Camera Isolation

One camera failure must not crash all cameras.

Future processing must run per-camera contexts (async tasks or isolated processes).  
Exception handlers at the camera-processing level must catch and log failures without propagating to other cameras.

---

## Rule 8 — Explainable Alerts

Whenever possible, an alert must have a clear, machine-readable reason.

Good: `{"event_type": "INTRUSION", "zone": "Restricted Zone A", "dwell_seconds": 43, "time_context": "NIGHT"}`  
Bad: `{"message": "Something suspicious happened"}`

This supports operator trust, audit logs, and future ML-based improvement.

---

## Rule 9 — Evidence-Backed Events

Important security events must eventually carry supporting evidence.

- Timestamp of detection
- Camera source
- Frame snapshot or short clip
- Track/object metadata

Events without evidence are difficult to review, dispute, or use legally.  
The evidence manager exists as a first-class component for this reason.

---

## Rule 10 — Don't Over-Engineer

Avoid unnecessary microservices, message brokers (Kafka, RabbitMQ), Kubernetes, or distributed architectures unless actual scale requirements justify them.

Start with a well-organized monolith. Split only when a real bottleneck or scale requirement appears.

---

## Rule 11 — Prefer Proven Components

Use mature open-source libraries and models when they solve the problem adequately.

- FastAPI over custom HTTP server
- Pydantic over manual serialization
- YOLO ecosystem over custom detector from scratch
- PostgreSQL over a novel database

Original contribution should be in the **application logic**, not in reinventing solved infrastructure.

---

## Rule 12 — Build Original Intelligence Where It Matters

IBVAP's unique value is not in object detection (which YOLO already does well).

Our original contribution is in:
- Spatial reasoning (zone/line logic)
- Event correlation (combining temporal + spatial + contextual information)
- Surveillance rules (tuned for border/security scenarios)
- Risk assessment logic
- Evidence management and operator workflow
- Deployment architecture for constrained environments

This is where engineering effort should focus in later milestones.

---

## Summary Table

| # | Rule | Keyword |
|---|------|---------|
| 1 | Never simulate AI output | No fake AI |
| 2 | All AI models replaceable | Modular AI |
| 3 | Optimize only after measurement | Measure first |
| 4 | No future milestones without approval | One at a time |
| 5 | Testing required per milestone | Test everything |
| 6 | No secrets in code | Security |
| 7 | Per-camera failure isolation | Camera isolation |
| 8 | Alerts must have machine-readable reasons | Explainability |
| 9 | Events must eventually carry evidence | Evidence-backed |
| 10 | Avoid unnecessary complexity | Don't over-engineer |
| 11 | Use proven libraries | Prefer proven |
| 12 | Build value in application logic | Our intelligence |
