# IBVAP — Milestone 12 Specification
## Command Center & Incident Visualization

**Upstream:** M1–M11 — FROZEN  
**Status:** READY FOR IMPLEMENTATION

---

## 1. Objective

M12 converts the validated IBVAP backend intelligence pipeline into an operational command-center interface.

The operator must be able to move from:

```text
Detection → Track → Spatial/Behavioral Event → SecurityEvent
→ Alert → M10 Evidence → M11 Incident Clip
```

without modifying the frozen backend.

---

## 2. Architectural Rule

M12 is strictly downstream of M1–M11.

```text
M1 → M2 → M3 → M4 → M5 → M6
                         ├→ M7
                         └→ M8
M6 → M10 → M11 → M12
```

M12 must NOT modify YOLO, ByteTrack, M5 geometry, M6 rules, M7 behavior detection, M8 scene analysis, M10 evidence generation, or M11 clip generation.

If a reproducible upstream defect is discovered, STOP and report it rather than silently changing the frozen milestone.

---

## 3. Primary Operator Goals

The command center must answer:

- Which cameras are online/offline?
- What objects are currently tracked?
- Are there active alerts?
- Where and when did an incident occur?
- Which rule generated it?
- What evidence and incident clip are available?
- What requires operator attention?

Alert priority must use the existing M6 severity:

```text
CRITICAL > HIGH > MEDIUM > LOW
```

---

## 4. M12 Components

```text
Command Center Frontend
          │
     REST / WebSocket
          │
       M12 API
          │
 ┌────────┼─────────┐
Camera   Alert    Evidence/Clip
Service  Service    Service
          │
       M1–M11
```

Components:

1. API Layer
2. Real-Time WebSocket Gateway
3. Incident/Alert Query Layer
4. Command Center Frontend
5. System Health / Diagnostics

---

## 5. API Boundary

Use:

```text
/api/v1
```

All API timestamps must use ISO-8601 UTC.

Example:

```text
2026-08-26T10:20:31Z
```

The frontend must never access SQLite directly.

```text
Frontend → API → Repository → SQLite
```

Reuse existing repositories where practical.

---

## 6. Camera APIs

### GET

```text
/api/v1/cameras
/api/v1/cameras/{camera_id}
```

Return where available:

- camera ID
- name
- location
- status
- source type
- scene state
- FPS
- last-frame timestamp
- active track count
- dropped frames
- processing latency
- current OPEN alert count

### Alert Count Semantics

The camera-card field:

```text
alerts
```

means **currently OPEN alerts for that camera**.

It does not mean:

- all-time alerts
- last-24-hour alerts
- total historical alerts

Historical counts must use explicitly named fields/filters.

Do not fabricate unavailable values.

---

## 7. Live Camera View

Support the existing configured local/IP camera or video sources without introducing a new ingestion architecture.

Display:

```text
Camera ID
Status
Scene State
FPS
Active Tracks
```

Unavailable stream:

```text
CAMERA OFFLINE
```

---

## 8. Track Visualization

Where available, display:

- Track ID
- Object class
- Bounding box
- Recent trajectory

Track IDs are camera/session scoped.

M12 must NOT imply that identical IDs across cameras represent the same physical object.

### Track Update Mechanism

M12 must NOT push every M4 bounding-box update/frame through WebSocket.

Use periodic track snapshots instead.

Initial target:

```text
2–5 updates/second/camera
```

The interval must be configurable.

A snapshot may contain:

- active track ID
- object class
- bounding box
- recent trajectory
- track state

Per-frame tracking remains inside the existing M2–M4 pipeline.

---

## 9. Alert APIs

```text
GET /api/v1/alerts
GET /api/v1/alerts/{alert_id}
```

Filters:

```text
status
severity
camera_id
from
to
rule_id
```

Return:

- alert ID
- SecurityEvent ID
- severity
- status
- rule ID
- camera ID
- track ID
- spatial object
- timestamp
- correlation ID
- metadata
- evidence references
- clip reference

---

## 10. Alert Lifecycle

Expose the existing M6 lifecycle:

```text
OPEN → ACKNOWLEDGED → RESOLVED
```

Provide API actions for:

```text
ACKNOWLEDGE
RESOLVE
```

Do not change M6 lifecycle semantics.

### Concurrent Transition Semantics

Lifecycle transitions must be conditional and idempotent.

Valid transitions:

```text
OPEN → ACKNOWLEDGED
ACKNOWLEDGED → RESOLVED
```

Repeating an already-applied transition should return the current state successfully rather than create a duplicate transition.

Examples:

```text
ACKNOWLEDGE(OPEN)
→ ACKNOWLEDGED

ACKNOWLEDGE(ACKNOWLEDGED)
→ ACKNOWLEDGED

RESOLVE(ACKNOWLEDGED)
→ RESOLVED

RESOLVE(RESOLVED)
→ RESOLVED
```

Invalid transitions must not silently overwrite state.

Database-level conditional updates must protect against concurrent requests and double-click races.

---

## 11. Real-Time Event Gateway

Use WebSocket:

```text
/ws/events
```

Support:

```text
NEW_ALERT
ALERT_UPDATED
ALERT_ACKNOWLEDGED
ALERT_RESOLVED
CAMERA_STATUS_CHANGED
SCENE_STATE_CHANGED
TRACK_SUMMARY_UPDATED
```

The UI must update without a full page refresh.

### Track Update Frequency

Do NOT push per-frame bounding-box updates through WebSocket.

Use periodic snapshots:

```text
2–5 updates/second/camera
```

with a configurable interval.

---

## 12. Real-Time Payload

All API and WebSocket timestamps must use:

```text
ISO 8601
UTC
```

Example:

```json
{
  "type": "NEW_ALERT",
  "alert_id": "alert_1024",
  "security_event_id": "evt_8842",
  "severity": "HIGH",
  "camera_id": "cam_test_01",
  "track_id": "cam_test_01-42",
  "rule_id": "restricted_zone_entry",
  "timestamp": "2026-08-26T10:20:31Z",
  "spatial_object_id": "zone_01",
  "correlation_id": "corr_52",
  "evidence_available": true,
  "clip_available": true
}
```

All filtering, timelines, database serialization and frontend date handling must preserve UTC semantics.

---

## 13. Incident Detail View

Selecting an alert opens an incident view containing:

### Header

```text
HIGH
Restricted Zone Entry
Camera: cam_test_01
Track: cam_test_01-42
Time: 10:20:31
```

### Evidence

- M10 annotated image
- M11 thumbnail
- M11 incident clip

### Context

- rule
- spatial object
- behavioral event, if present
- scene state
- correlation ID
- metadata

### Timeline

```text
10:20:25 Track observed
10:20:27 Zone approach
10:20:31 ZONE_ENTER
10:20:31 SecurityEvent
10:20:31 Alert OPEN
10:20:32 Evidence persisted
10:20:33 Clip persisted
```

Only show events that actually exist.

---

## 14. Evidence Viewer

Expose M10:

- original evidence
- annotated evidence
- evidence ID
- timestamp
- camera ID
- track ID
- evidence quality
- file status

If unavailable:

```text
EVIDENCE UNAVAILABLE
```

Never fabricate evidence.

---

## 15. Incident Clip Viewer

Expose M11 clip:

- thumbnail
- browser video player
- duration
- camera
- event timestamp
- clip status

Support existing states:

```text
PENDING
PROCESSING
PERSISTED
PARTIAL
FAILED
SOURCE_UNAVAILABLE
ENCODER_UNAVAILABLE
```

If `PARTIAL`, visibly display:

```text
PARTIAL INCIDENT CLIP
```

with requested and actual start/end times.

### HTTP Range Support

The clip endpoint must support browser byte-range requests:

```text
Accept-Ranges: bytes
Range: bytes=...
Content-Range: ...
```

This is required for efficient MP4 streaming and seeking/scrubbing.

The backend must not read the complete MP4 into memory to serve browser playback.

---

## 16. Camera Command Center

Main screen should contain a camera grid.

Each card should show:

```text
CAMERA 01   ONLINE
LIVE VIEW
Tracks: 8
Scene: DAY
FPS: 29.7
Alerts: 2
```

Here `Alerts: 2` means **2 currently OPEN alerts**.

Clicking a camera opens its detailed view.

---

## 17. Camera Health

Use actual backend state:

```text
ONLINE
DEGRADED
OFFLINE
```

Where available show:

- FPS
- last frame time
- processing latency
- queue depth
- dropped frames
- scene state

---

## 18. System Health

Provide:

```text
M2 Camera Ingestion       HEALTHY
M3 AI Detection           HEALTHY
M4 Tracking               HEALTHY
M5 Spatial Engine         HEALTHY
M6 Event Pipeline         HEALTHY
M7 Behavioral Engine      HEALTHY
M8 Scene Engine           HEALTHY
M10 Evidence              HEALTHY
M11 Incident Clips        HEALTHY
```

Health must be based on real service state.

---

## 19. Historical Search

Support:

```text
camera
severity
alert status
rule
track ID
date/time
```

ANPR search is intentionally excluded because M9 remains deferred.

Do not create a fake number-plate search feature.

### Pagination

All historical/list endpoints must be bounded.

Minimum:

```text
limit
offset
```

Recommended:

```text
default limit = 50
maximum limit = 200
```

A cursor implementation is acceptable if already supported.

Never return an unbounded historical alert/event list.

---

## 20. Track-Centric View

For a selected track display:

- Track ID
- camera ID
- object class
- current bounding box
- trajectory
- first seen
- last seen
- associated events
- alerts
- evidence
- clips

Clearly label track identity as camera/session scoped.

---

## 21. Spatial Context

If configured, display:

- cameras
- zones
- tripwires
- alert locations
- current tracks

Use existing M5 configuration.

No advanced GIS requirement is necessary.

Do not fabricate coordinates.

---

## 22. UI Technology

Use the existing repository stack if present.

Otherwise recommended:

```text
React
TypeScript
Vite
```

Do not introduce unnecessary framework complexity.

---

## 23. UI Design

The command center should look like a professional security operations interface.

Priorities:

1. Dark operational theme
2. High information density
3. Clear severity hierarchy
4. Large live-video areas
5. Minimal decorative animation
6. Fast alert recognition
7. Easy evidence access
8. Responsive layout

Avoid excessive decorative effects.

The interface must communicate operational information first.

---

## 24. WebSocket Reliability

Connection states:

```text
CONNECTED
DISCONNECTED
RECONNECTING
```

After reconnection, perform a full state resynchronization covering at minimum:

```text
current OPEN alerts
camera status
scene state
active track summaries
```

This prevents stale state after a disconnected period.

Do not rely only on the next natural WebSocket event to repair state.

---

## 25. Security Boundary

M12 is initially an internal command-center prototype.

### Default Network Boundary

Bind the API to:

```text
127.0.0.1
```

by default.

The default deployment is therefore localhost-only.

If a non-localhost address is explicitly configured:

1. Emit a clear startup warning.
2. Require a configurable API key/token for remote API access.

This is intentionally not a full IAM system.

Do not add:

- public internet exposure
- complex IAM
- biometric authorization
- external authentication providers

But must:

- protect database credentials
- prevent path traversal
- validate artifact IDs
- serve only approved evidence/clip artifacts
- protect ACKNOWLEDGE/RESOLVE when remotely exposed

---

## 26. Safe Artifact Serving

Never expose raw filesystem paths.

Bad:

```text
/files/C:/Users/.../clip.mp4
```

Good:

```text
/api/v1/clips/{clip_id}
```

The backend resolves the artifact safely.

---

## 27. Performance Targets

Target:

```text
API typical response < 200 ms
WebSocket event delivery < 500 ms
```

The frontend must remain responsive while alerts, cameras, evidence and clips are updated.

Do not load complete MP4 files into RAM.

### Clip Streaming

Use HTTP Range requests as specified in Section 15.

---

## 28. Demo Assets

Validate with existing:

```text
videoplayback.mp4
daytime traffic video
night video
close-range traffic/people video
```

Use real M10/M11 artifacts where available.

Synthetic events are permitted only when clearly labelled:

```text
DEMO / SYNTHETIC
```

Never fabricate real incidents.

---

## 29. Required Demonstration

The primary demo must show:

```text
LIVE CAMERA
    ↓
OBJECT DETECTED
    ↓
TRACK CREATED
    ↓
SPATIAL / BEHAVIOR EVENT
    ↓
ALERT APPEARS
    ↓
OPERATOR OPENS ALERT
    ↓
M10 EVIDENCE
    ↓
M11 INCIDENT CLIP
```

This is the core M12 demonstration.

---

## 30. API Testing

Test:

- camera list/detail
- alert list/detail
- evidence retrieval
- clip retrieval
- acknowledge
- resolve
- invalid IDs
- path traversal attempts
- backend errors
- pagination limits
- concurrent lifecycle requests

---

## 31. WebSocket Testing

Test:

- connection
- new alert
- alert update
- reconnect
- missed-event recovery
- camera state resynchronization
- scene state resynchronization
- track snapshot resynchronization

---

## 32. Frontend Testing

Test:

- camera grid
- live view
- alert rendering
- severity ordering
- incident detail
- evidence viewer
- clip viewer
- video seeking/scrubbing
- offline camera
- missing evidence
- missing clip
- partial clip
- WebSocket disconnect
- reconnect state recovery

---

## 33. End-to-End Test

Run:

```text
M2 → M3 → M4 → M5 → M6 → M7 → M8 → M10 → M11 → M12
```

Generate a real SecurityEvent where possible.

Confirm:

```text
Alert
 ↓
Evidence
 ↓
Clip
```

IDs and timestamps must remain consistent.

---

## 34. Regression Requirements

After M12 implementation verify:

- M1 tests pass
- M2 ingestion works
- M3 detection works
- M4 tracking works
- M5 spatial events work
- M6 alerts work
- M7 behavior works
- M8 scene state works
- M10 evidence works
- M11 clips work

Do not modify frozen milestones to hide regression failures.

---

## 35. No Silent Fabrication

M12 must never invent:

- camera locations
- object classes
- alert severity
- evidence
- clips
- track identities
- timestamps
- scene state

Unavailable information must be displayed as:

```text
UNAVAILABLE
```

---

## 36. Configuration

Avoid hardcoded:

- camera IDs
- paths
- ports
- URLs
- database locations
- authentication secrets

Use environment/configuration variables:

```text
IBVAP_API_HOST=127.0.0.1
IBVAP_API_PORT
IBVAP_DATABASE_PATH
IBVAP_EVIDENCE_PATH
IBVAP_CLIP_PATH
IBVAP_WS_PATH
IBVAP_API_KEY
IBVAP_TRACK_UPDATE_INTERVAL_MS
```

The API key is required only when non-localhost exposure is explicitly enabled.

Provide sensible local defaults.

---

## 37. Deliverables

Produce:

```text
app/api/
app/api/routes/
app/api/services/
app/api/websocket/

frontend/
  src/
  components/
  pages/
  services/
  hooks/

tests/m12/

artifacts/m12/
```

Follow existing repository conventions where they differ.

---

## 38. Acceptance Criteria

### API

- [ ] Camera API works
- [ ] Alert API works
- [ ] Evidence API works
- [ ] Clip API works
- [ ] Alert lifecycle works
- [ ] No raw filesystem paths exposed
- [ ] Pagination enforced
- [ ] UTC timestamps enforced

### Real-Time

- [ ] WebSocket connects
- [ ] New alerts appear without refresh
- [ ] Reconnection works
- [ ] Missed events recover
- [ ] Camera/scene/track state resynchronizes
- [ ] Track updates are periodic, not per-frame

### Command Center

- [ ] Camera grid
- [ ] Live video
- [ ] Track information
- [ ] Alert panel
- [ ] Severity hierarchy
- [ ] Incident detail
- [ ] Timeline
- [ ] Evidence viewer
- [ ] Clip viewer
- [ ] MP4 seeking/scrubbing

### Reliability

- [ ] Offline camera handled
- [ ] Missing evidence handled
- [ ] Missing clip handled
- [ ] Partial clip clearly marked
- [ ] WebSocket failure handled
- [ ] Backend failure handled
- [ ] Concurrent ACK/RESOLVE handled safely

### Security

- [ ] Localhost-only default
- [ ] Remote exposure warning
- [ ] API key required for explicit remote exposure
- [ ] Path traversal prevented
- [ ] Database inaccessible from frontend
- [ ] Only approved artifacts served

### Regression

- [ ] M1–M11 regression passes

---

## 39. Performance Acceptance

Demonstrate:

```text
API typical response       < 200 ms
WebSocket event delivery   < 500 ms
No blocking of M6/M10/M11
```

These are M12 interface targets and must not be achieved by modifying frozen backend processing.

---

## 40. Visual Demonstration Artifacts

Save:

```text
artifacts/m12/demo/
```

At minimum:

1. Command center overview
2. Live camera grid
3. Active alert
4. Incident detail
5. M10 evidence
6. M11 clip playback
7. Timeline
8. Camera offline state
9. Partial clip state
10. System health panel
11. WebSocket reconnect demonstration
12. MP4 seek/scrub demonstration

---

## 41. Completion Report

Create:

```text
artifacts/m12/milestone12_completion.md
```

Include:

- architecture
- API endpoints
- frontend architecture
- WebSocket implementation
- repository usage
- security boundary
- authentication/access-control behavior
- tests
- pagination
- clip streaming/range support
- track snapshot strategy
- performance
- screenshots/demo artifacts
- M1–M11 regression
- known limitations

Use only:

```text
PASS
FAIL
PARTIAL
NOT OBSERVED
DEFERRED
```

Never turn an untested feature into PASS.

---

## 42. Independent Validation

Before freezing M12, perform a separate read-only validation pass covering:

- API contracts
- frontend/backend integration
- real-time alerts
- evidence access
- clip playback
- HTTP Range seeking
- lifecycle concurrency
- pagination
- security boundaries
- WebSocket reconnection/resync
- track snapshot frequency
- performance
- M1–M11 regression

The validator must not silently fix defects.

---

## 43. STOP Condition

After implementation and independent validation:

**STOP.**

Do not begin another milestone automatically.

Do not modify M1–M11 unless a reproducible M12 integration defect explicitly requires it.

---

# M12 Status

**READY FOR IMPLEMENTATION**

Implementation → Independent Validation → Review → Freeze
