# IBVAP Architecture Document

**Version:** Milestone 1  
**Status:** Foundation established. AI layers are defined as boundaries only.

---

## 1. Overview

IBVAP (Intelligent Border Video Analytics Platform) is a modular, software-defined surveillance intelligence system. It ingests video streams from standard IP cameras and applies AI-powered analytics to detect, track, and alert on security-relevant events.

The core processing philosophy is:

```
Detect → Track → Understand → Decide → Alert → Record Evidence
```

The final system must be deployable in environments with limited/unreliable internet connectivity. All core intelligence runs locally.

---

## 2. Architectural Principles

| Principle | Rationale |
|-----------|-----------|
| **Modular AI** | Any detector, tracker, or OCR engine can be replaced independently |
| **Camera isolation** | A failure in one camera must not affect others |
| **Configuration-driven** | Surveillance rules (zones, thresholds, hours) come from config, not code |
| **Hardware-agnostic** | Works with existing IP cameras over RTSP — no proprietary hardware |
| **Local-first** | Inference, events, evidence, and dashboard all function without internet |
| **Structured contracts** | All data passing between layers uses typed domain models |

---

## 3. Processing Pipeline

```
CCTV / Video Sources
    ↓
┌─────────────────────────────┐
│ Layer 1: Video Ingestion    │  Acquires frames from sources
│   StreamManager             │  (file, webcam, RTSP)
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 2: Frame Processing   │  Frame representation, timestamps,
│   Frame domain model        │  resolution, preprocessing hooks
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 3: AI Perception      │  Person, vehicle, face, plate detection
│   BaseDetector interface    │  ← Future: YOLO, RetinaFace
│   → Detection domain model  │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 4: Tracking           │  Persistent object identities across frames
│   BaseTracker interface     │  ← Future: ByteTrack, BoT-SORT
│   → Track domain model      │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 5: Spatial Intel      │  Zone containment, line crossing,
│   SpatialEngine             │  direction, region-of-interest logic
│   Zone / VirtualLine models │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 6: Event Engine       │  Converts observations → security events
│   EventEngine               │  Intrusion, loitering, ANPR, night movement
│   → Event domain model      │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 7: Risk Engine        │  Assigns severity to events
│   RiskEngine                │  LOW / MEDIUM / HIGH / CRITICAL
│   → RiskAssessment model    │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 8: Evidence Mgmt      │  Snapshots, clips, metadata per event
│   EvidenceManager           │
│   → Evidence domain model   │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 9: Persistence        │  Database storage (future: PostgreSQL)
│   (Future Milestone 14)     │  Cameras, events, alerts, evidence
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 10: API / WebSocket   │  REST API + real-time push
│   FastAPI routers           │  Camera mgmt, events, alerts, config
│   WebSocket endpoint        │  Real-time dashboard notifications
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Layer 11: Frontend          │  Security operator dashboard
│   React + Vite              │  Camera grid, alerts, history, config
│   (Future Milestone 15)     │
└─────────────────────────────┘
```

---

## 4. Module Responsibilities

### `app/domain/`
Pure typed domain contracts. No business logic. No database ORM. No framework coupling.  
These are the shared vocabulary of the entire system.

### `app/api/`
HTTP boundary. Routes map URLs to service calls. Routers do not contain business logic.

### `app/services/`
Business logic. Services orchestrate domain models, call layer interfaces, and coordinate actions. Services do not know about HTTP.

### `app/ingestion/`
Video acquisition boundary. Manages per-camera streams. Decoupled from AI inference.

### `app/perception/`
AI perception interface only. Future detectors implement `BaseDetector`. The rest of the system only interacts through the `Detection` domain model — never through model-specific APIs.

### `app/tracking/`
Tracker interface. Future trackers implement `BaseTracker`. Consumes `Detection`, produces `Track`. Independent of the specific AI detector used.

### `app/spatial/`
Evaluates geometric relationships between tracks and configured zones/lines.  
Does not call neural networks. Operates on structured `Track` and `Zone` objects.

### `app/events_engine/`
Converts spatial observations + temporal state → `Event` objects.  
Does not run inference. Consumes structured inputs from upstream layers.

### `app/risk/`
Assigns `RiskAssessment` to events. Configurable scoring logic.  
Separated so the scoring system can be tuned independently.

### `app/evidence/`
Associates events with supporting artifacts (snapshots, clips, metadata).  
Controls retention and storage strategy.

---

## 5. AI Integration Points

Future AI integrations connect at these defined boundaries:

| Future Technology | Integration Point | Interface |
|---|---|---|
| YOLO (object detection) | `app/perception/` | `BaseDetector.detect()` |
| ByteTrack / BoT-SORT | `app/tracking/` | `BaseTracker.update()` |
| PaddleOCR / EasyOCR | Within perception or ANPR module | Returns text string |
| RetinaFace / SCRFD | Separate face-detection module | `BaseDetector` subclass |
| NVIDIA TensorRT | Optimization of perception modules | Transparent to callers |
| OpenCV / FFmpeg | `app/ingestion/` | `StreamManager` implementations |

**Critical rule:** No other layer imports PyTorch, CUDA, or model-specific APIs. All AI results flow as typed domain objects through the defined interfaces.

---

## 6. Failure Isolation Strategy

Each camera will run in an isolated processing context (future: separate async tasks or processes).

- A camera connection failure is caught and logged by `StreamManager` — it does not propagate to other camera contexts.
- An inference failure in `BaseDetector` raises `PerceptionException` — caught by the camera's processing loop — other cameras continue.
- An OCR failure is isolated to the ANPR sub-pipeline — vehicle detection continues.
- An event processing failure is isolated to the specific event rule — other rules continue.

All layers log failures using the structured logger with camera context included.

---

## 7. Multi-Camera Architecture

Every runtime domain model carries a `camera_id`:

- `Frame.camera_id`
- `Detection.camera_id`
- `Track.camera_id`
- `Event.camera_id`
- `Evidence.camera_id`

This ensures all data is traceable to its source camera and enables future parallel processing of N cameras.

Cross-camera re-identification is out of scope until Milestone 17.

---

## 8. Configuration Strategy

All tunable parameters are externalized:

- Application settings → `.env` / environment variables (loaded via `pydantic-settings`)
- Surveillance rules (thresholds, zone configs) → database records (future)
- Model paths → configuration (never hard-coded)
- Credentials → environment only, never source code

---

## 9. Real-Time Communication

The WebSocket endpoint (`/ws`) is the boundary for future real-time dashboard updates.

Future events that will be pushed via WebSocket:
- New alert created
- Alert state changed
- Camera stream state change
- System health change
- Real-time detection counts

The frontend subscribes to this channel rather than polling REST endpoints for live data.

---

## 10. Deployment Philosophy

- **Local-first:** Core inference, events, evidence, and dashboard all function without internet.
- **Edge-deployable:** Target runs on a local node near cameras.
- **Optional central sync:** Local nodes may optionally sync with a central command center.
- **Docker-ready:** (Future Milestone 19) Full Docker deployment for consistent environments.
- **GPU-ready:** NVIDIA GPU (RTX 4060-class) available. TensorRT/ONNX optimization deferred until after baseline pipeline is working.

---

## 11. Current Limitations (Milestone 1)

- No video frame acquisition (Milestone 2)
- No AI inference (Milestone 3)
- No object tracking (Milestone 4)
- No zone/line evaluation (Milestone 5)
- No event generation (Milestone 6)
- No risk scoring (Milestone 12)
- No evidence capture (Milestone 13)
- No database persistence (Milestone 14)
- No production dashboard (Milestone 15)
- No PostgreSQL integration
- No authentication/authorization
- No Docker deployment

All API endpoints return `HTTP 501 Not Implemented` with an explanatory message.
