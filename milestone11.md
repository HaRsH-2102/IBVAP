# IBVAP — Milestone 11 Specification
## Evidence Video Clip Generation & Incident Reconstruction

**Status:** SPECIFICATION / NOT STARTED  
**Upstream:** M1–M10 FROZEN  
**ANPR:** M9 DEFERRED  
**Previous:** M10 — Evidence & Event Intelligence  
**Next:** M12 — Command Center / Incident Visualization

---

## 1. Objective

Extend M10's still-image evidence into short, persistent incident video clips.

M11 transforms an existing `SecurityEvent` + `EvidencePackage` into a reproducible incident clip containing:
- pre-event context
- the event itself
- post-event context
- event metadata
- visual annotations
- deterministic timestamps
- persistent clip metadata

The goal is to let an operator answer:

> **What happened immediately before, during, and after the detected incident?**

M11 builds on M10. It does **not** reimplement detection, tracking, spatial intelligence, behavioral intelligence, ANPR, or cross-camera Re-ID.

---

## 2. Architectural Boundary

```text
M3 Detection
      ↓
M4 Tracking
      ↓
M5 Spatial
      ↓
M6 SecurityEvent / Alert
      ↓
M7 Behavioral
      ↓
M8 Scene
      ↓
M10 EvidencePackage
      ↓
M11 Incident Clip
```

M11 is strictly downstream of M10.

---

## 3. Core Domain Contract

Create:

`app/domain/incident_clip.py`

The contract should contain at least:

- `clip_id`
- `security_event_id`
- `alert_id`
- `evidence_id`
- `camera_id`
- `track_id`
- `event_type`
- `event_timestamp`
- `clip_start_timestamp`
- `clip_end_timestamp`
- `pre_event_seconds`
- `post_event_seconds`
- `duration_seconds`
- `source_video_reference`
- `clip_path`
- `thumbnail_path`
- `status`
- `created_at`
- `metadata`

Optional information must remain optional. Never fabricate missing data.

---

## 4. Clip Lifecycle

Use an explicit status enum:

```text
REQUESTED
QUEUED
CAPTURING
ENCODING
PERSISTED
FAILED
SOURCE_UNAVAILABLE
PARTIAL
```

Normal flow:

```text
REQUESTED → QUEUED → CAPTURING → ENCODING → PERSISTED
```

Failures must never invalidate the originating SecurityEvent or Alert.

---

## 5. Default Clip Window

Configurable defaults:

```text
pre_event_seconds = 5
post_event_seconds = 5
minimum_clip_duration_seconds = 2
maximum_clip_duration_seconds = 30
```

The default clip is therefore approximately 10 seconds.

The event timestamp must remain inside the resulting clip.

---

## 6. Event-Centered Timeline

```text
          EVENT
            │
            ▼
───────┬─────┬───────
       │     │
    -5 sec   +5 sec
       │     │
       └─────┘
       10 sec
```

If the event is near the beginning/end of the source:
- capture whatever footage exists
- do not fabricate frames
- record actual duration
- mark `PARTIAL` when the requested window cannot be fully satisfied

---

## 7. Source Video Requirement

M11 requires the original video source or an equivalent seekable recording.

M10 JPEG evidence alone cannot reconstruct a real clip.

Maintain:

`source_video_reference`

Supported initial sources may include:
- local video path
- recorded camera segment
- configured video archive

### Live / RTSP Scope

M11 does not implement a new rolling recorder.

For a live/RTSP source, the available recording buffer must cover the requested event window.

If only part of the requested window is available:

```text
some requested footage available
        ↓
PARTIAL
```

If no usable source segment containing the event is available:

```text
SOURCE_UNAVAILABLE
```

The system must never silently shorten the requested window.

The actual available start/end timestamps must be recorded in the clip metadata.

Do not implement a full rolling recorder in M11.

---

## 8. Timestamp / Frame Mapping

Record:

- source FPS
- source frame count when available
- source duration
- requested event timestamp
- nearest source frame timestamp
- event frame index
- clip start frame
- clip end frame

The event timestamp must never be treated as a frame number without conversion.

---

## 9. Timestamp Tolerance

Configurable:

```text
clip_event_frame_tolerance_ms = 100
clip_max_seek_error_ms = 200
```

Classification:

```text
seek error <= 100 ms
    → EXACT_EVENT_FRAME

100 ms < seek error <= 200 ms
    → NEAREST_EVENT_FRAME

seek error > 200 ms
    → SOURCE_ALIGNMENT_UNAVAILABLE
```

If alignment is unavailable, do not silently produce a misleading clip.

---

## 10. Clip Generation

For file-based video:

1. open source
2. determine FPS/duration
3. map event timestamp to frame
4. determine start/end frames
5. seek/capture required range
6. annotate frames
7. encode clip
8. generate thumbnail
9. validate output
10. persist metadata

For live sources, use an existing recording/buffer only.

---

## 11. Annotation

The generated clip should display, where available:

- camera ID
- timestamp
- event type
- track ID
- object class
- bounding box
- zone/line ID
- behavioral state
- scene state

Example:

```text
CAM: cam_test_01
TIME: 00:01:24.320
EVENT: ZONE_ENTER
TRACK: cam_test_01-42
OBJECT: CAR
ZONE: restricted_zone_01
SCENE: NIGHT
```

Annotate frame copies only. Never modify the source video.

---

## 12. Track Visualization

If M10 contains trajectory information, M11 may render:
- current bounding box
- recent trajectory
- track ID

### Per-Frame Annotation Rule

Dynamic tracking overlays must be updated **per frame** using the available M10 trajectory/evidence information.

Do **not** burn one static bounding box onto every frame of the clip.

For each frame:

```text
available track position
        ↓
render current bounding box / trajectory
```

If a valid position is unavailable for a particular frame:

```text
omit dynamic track overlay for that frame
```

Do not interpolate or invent coordinates unless explicitly provided by the evidence contract.

Static metadata such as event type, camera ID, and SecurityEvent ID may remain constant across the clip.

Use only existing M10 data. Do not rerun tracking.

---

## 13. Event Marker

The event moment should be visually identifiable, for example:

```text
EVENT @ 00:05.240
```

The marker must not obscure the relevant object.

---

## 14. Thumbnail

Every successfully persisted clip should generate one thumbnail.

Preferred frame: event frame.

Fallback: nearest available frame.

Store:

`thumbnail_path`

---

## 15. Storage

Extend M10's evidence structure:

```text
evidence/
  <camera_id>/
    <date>/
      <evidence_id>/
        original.jpg
        annotated.jpg
        incident_clip.mp4
        thumbnail.jpg
        metadata.json
```

Do not create an unrelated second evidence hierarchy.

---

## 16. Clip Metadata

Persist in SQLite:

- clip ID
- SecurityEvent ID
- Alert ID
- Evidence ID
- camera ID
- track ID
- event type
- event timestamp
- clip start/end
- requested/actual duration
- source FPS
- source frame count
- start/event/end frame
- clip path
- thumbnail path
- status
- created timestamp

Do not duplicate complete SecurityEvent/Alert records.

---

## 17. Idempotency

A SecurityEvent must not create multiple identical clips.

Use a database-level UNIQUE constraint on:

`security_event_id`

Application checks are only an optimization.

Retry behavior:

```text
existing PERSISTED clip
        ↓
reuse existing clip
```

Do not encode it again unnecessarily.

---

## 18. Queue Architecture

Clip generation must not block M6.

```text
SecurityEvent
      ↓
M10 EvidencePackage
      ↓
M11 Clip Queue
      ↓
Clip Worker
      ↓
Video extraction
      ↓
Annotation
      ↓
Encoding
      ↓
Storage
      ↓
SQLite
```

Suggested defaults:

```text
clip_queue_capacity = 10
clip_worker_count = 1
```

Both configurable.

---

## 19. Queue-Full Behavior

If the queue is full:

- SecurityEvent remains valid.
- Alert remains valid.
- M10 EvidencePackage remains valid.
- clip request gets an explicit failure/queued state.
- reason: `CLIP_QUEUE_FULL`
- log SecurityEvent ID, Evidence ID, camera ID, track ID.

Suggested:

```text
max_clip_retries = 1
clip_retry_backoff_seconds = 2
```

### Retry Policy

Retries are bounded and classified by failure type.

**Retryable:**
- `CLIP_QUEUE_FULL`
- temporary filesystem/storage failure
- temporary SQLite busy/lock condition
- transient encoder/resource failure

**Not retryable:**
- source file permanently missing
- unsupported/invalid source
- event timestamp cannot be aligned within the configured maximum
- encoder unavailable as a system capability
- invalid configuration

A retry must use the configured backoff rather than repeatedly retrying immediately.

Record:

```text
retry_count
failure_reason
```

A queue-full request must never be silently discarded.

---

## 20. Source Unavailable

If the source cannot be accessed:

```text
status = SOURCE_UNAVAILABLE
failure_reason = SOURCE_NOT_FOUND
```

Do not delete M10 evidence, SecurityEvents, or Alerts.

---

## 21. Partial Clips

Example:

Requested:

```text
-5 sec → +5 sec
```

Available:

```text
-2 sec → +5 sec
```

Then:

```text
status = PARTIAL
actual_duration = 7 sec
```

Record the discrepancy in metadata.

---

## 22. Encoding

Recommended output:

```text
MP4
```

Use a codec actually available in the environment.

### Encoder Availability

Encoder availability must be checked before normal M11 processing begins.

If the required encoder is unavailable:

```text
M11 clip generation → DISABLED
```

The worker must not repeatedly crash or retry an unavailable system capability.

Clip requests receive:

```text
status = FAILED
failure_reason = ENCODER_UNAVAILABLE
```

The failure is logged clearly, but:

- M6 continues processing SecurityEvents.
- Alerts continue operating.
- M10 evidence generation continues.
- M11 remains isolated.

The system should log the encoder capability failure once per worker/session rather than repeatedly producing identical crash messages.

Encoder availability is a configuration/environment capability failure, not a retryable per-clip failure.

Record:
- codec
- resolution
- FPS
- duration
- file size

---

## 23. Output Validation

After encoding verify:

- file exists
- size > 0
- video opens
- frame count > 0
- valid FPS
- valid duration
- event frame is present
- thumbnail exists

If validation fails:

`FAILED`

Never mark an invalid artifact `PERSISTED`.

---

## 24. Filesystem / Database Ordering

Required order:

```text
Generate clip
    ↓
Validate clip
    ↓
Generate thumbnail
    ↓
Validate thumbnail
    ↓
Commit SQLite metadata
```

Recovery states:

```text
DB + clip + thumbnail → VALID
DB + missing clip → ARTIFACT_MISSING
clip + no DB row → ORPHANED_ARTIFACT
```

Do not silently delete orphaned artifacts.

---

## 25. SQLite Concurrency

Reuse M10 persistence strategy:

- WAL enabled
- busy timeout configured
- thread-safe access
- serialized writes where practical
- no unsafe shared connections

M11 must not reintroduce M6's synchronous disk bottleneck into the event path.

---

## 26. Failure Isolation

A clip failure must never:
- crash M6
- invalidate an Alert
- invalidate M10 evidence
- stop other clip jobs

---

## 27. SecurityEvent / Alert Relationship

Maintain:

```text
SecurityEvent
      ↓
Alert
      ↓
EvidencePackage
      ↓
IncidentClip
```

`security_event_id` remains the primary incident anchor.

---

## 28. Multi-Rule Handling

If one physical event produces multiple SecurityEvents, keep them as distinct logical events.

They may reference the same source timestamp/frame, but M11 must not incorrectly merge them.

---

## 29. Multi-Camera Isolation

Every clip retains:

`camera_id`

Track IDs remain camera-local.

No cross-camera identity is implemented.

---

## 30. Privacy

M11 adds no biometric processing.

Do not implement:
- face recognition
- identity inference
- demographic classification

---

## 31. Configuration

Suggested defaults:

```text
incident_clip_enabled = true
pre_event_seconds = 5
post_event_seconds = 5
minimum_clip_duration_seconds = 2
maximum_clip_duration_seconds = 30
clip_event_frame_tolerance_ms = 100
clip_max_seek_error_ms = 200
clip_queue_capacity = 10
clip_worker_count = 1
max_clip_retries = 1
clip_format = mp4
thumbnail_enabled = true
```

No developer-specific absolute paths.

---

## 32. Testing Strategy

Test:

### A — Domain
Contract, serialization, lifecycle, timestamps.

### B — Frame Mapping
Known FPS + event timestamp → correct frame.

### C — Normal Clip
5 seconds pre + event + 5 seconds post.

### D — Start Boundary
Event near frame 0 → `PARTIAL`.

### E — End Boundary
Event near EOF → `PARTIAL`.

### F — Missing Source
→ `SOURCE_UNAVAILABLE`.

### G — Annotation
Bounding box, track, camera, event, timestamp.

### H — Thumbnail
Event-frame thumbnail.

### I — Idempotency
Same SecurityEvent twice → one clip.

### J — Queue Full
→ explicit `CLIP_QUEUE_FULL`.

### K — Encoding Failure
→ `FAILED`, never false `PERSISTED`.

### L — Restart Recovery
Metadata and files remain valid.

### M — Reconciliation
DB+file, DB+missing file, file+no DB.

### N — Multi-Event
Two SecurityEvents at similar timestamps remain distinct.

### O — Live/RTSP Partial Buffer
Simulate a source whose retained buffer begins after the requested pre-event timestamp.

Verify:
- available footage is preserved
- status is `PARTIAL`
- actual start timestamp is recorded
- requested window is not silently redefined

### P — Retry Classification
Verify:
- queue full retries once with backoff
- transient storage failure retries once
- permanent source failure does not retry
- encoder-unavailable does not repeatedly retry

### Q — Per-Frame Annotation
Verify bounding boxes/trajectory overlays follow changing track positions frame-by-frame.

Verify no single static box is burned across the entire clip.

### R — Disk Backpressure
Simulate free disk below `minimum_free_disk_gb`.

Verify:
- M11 clip request becomes `FAILED`
- reason is `INSUFFICIENT_DISK_SPACE`
- M6 continues
- M10 continues

### S — Encoder Unavailable
Simulate an unavailable encoder.

Verify:
- M11 gracefully disables clip generation
- clip requests receive `ENCODER_UNAVAILABLE`
- worker does not repeatedly crash
- M6 continues
- M10 continues

---

## 33. Real-Video Validation

M11 MUST be visibly demonstrated using:

1. Daytime traffic video
2. Nighttime traffic video
3. Close-range traffic video

Reuse established canonical assets.

Use:

`IBVAP_TEST_VIDEO`

or repository-relative paths.

No hardcoded developer paths.

---

## 34. Required Visual Demonstration

Show:

```text
Original video
      ↓
Selected incident
      ↓
Incident clip
      ↓
Event marker
      ↓
Bounding box / track
      ↓
Event metadata
```

For each clip inspect:
- clip
- thumbnail
- event type
- timestamp
- camera ID
- track ID
- object class
- spatial context
- behavioral context
- scene state

Terminal output alone is insufficient.

---

## 35. Required Demonstration Events

Attempt naturally:

- `ZONE_ENTER`
- `ZONE_EXIT`
- `LINE_CROSS`
- `LOITERING`
- `RESTRICTED_ZONE_DWELL`
- a `NIGHT` event

If not naturally observed:

`NOT OBSERVED IN SELECTED VIDEO`

A clearly labelled synthetic test may validate deterministic clip-window mechanics, but must not be presented as a real-video observation.

---

## 36. Performance Metrics

Measure separately:

- queue wait
- source seek
- frame extraction
- annotation
- encoding
- thumbnail generation
- filesystem write
- SQLite write
- total clip generation

Report:

```text
M6 critical-path latency
vs.
M11 asynchronous clip latency
```

Do not combine them.

---

## 37. Storage Metrics

Report:
- clips generated
- persisted
- partial
- failed
- source-unavailable
- average clip size
- maximum clip size
- total storage
- average generation time

---

## 38. Resource Bounds

Do not:
- load entire source videos into RAM
- retain unlimited frames
- create unbounded queues

Process frames incrementally.

### Clip Storage / Disk Backpressure

MP4 clips can consume substantially more storage than M10 JPEG evidence.

Add:

```text
clip_retention_enabled = false
clip_retention_days = 30
minimum_free_disk_gb = 5
```

Retention is **disabled by default** in M11 unless explicitly enabled.

If retention is enabled, only M11 clip artifacts are eligible for its cleanup policy.

Retention cleanup must never delete:
- SecurityEvents
- Alerts
- M10 evidence records

If free disk space falls below `minimum_free_disk_gb`:

```text
new clip generation → FAILED
failure_reason = INSUFFICIENT_DISK_SPACE
```

M6 and M10 must continue operating normally.

No unbounded clip storage growth is permitted.

---

## 39. Logging

Log:
- requested
- queued
- started
- completed
- failed
- source unavailable
- queue full
- encoding failure
- storage failure
- reconciliation

Include clip ID, SecurityEvent ID, Evidence ID, camera ID, track ID.

Do not log raw video bytes.

---

## 40. Artifacts

Save validation results under:

```text
artifacts/m11/
    daytime/
    nighttime/
    close_range/
    thumbnails/
    metadata/
    failures/
    reports/
```

Example:

```text
incident_001.mp4
incident_001_thumbnail.jpg
incident_001.json
```

---

## 41. Regression Testing

M11 must not change:
- M1 domain contracts
- M2 ingestion
- M3 detection
- M4 tracking
- M5 spatial
- M6 rules/alerts
- M7 behavior
- M8 scene
- M10 evidence

Any regression is a blocker.

---

## 42. Explicit Non-Goals

M11 MUST NOT implement:
- ANPR/OCR
- vehicle Re-ID
- cross-camera identity
- global vehicle IDs
- dashboard
- command center
- maps
- new detection models
- new tracking models
- advanced behavioral reasoning
- live DVR/rolling recorder
- cloud storage

---

## 43. M12 Integration

M12 will consume `IncidentClip` and expose it through the future command center.

M12 may display:
- alert
- event
- evidence image
- incident clip
- thumbnail
- camera
- timestamp
- track
- object
- behavior
- scene state

M11 remains UI-independent.

---

## 44. Future ANPR Integration

M9 remains deferred.

Future flow:

```text
ANPREvent
   ↓
M6 SecurityEvent
   ↓
M10 Evidence
   ↓
M11 IncidentClip
```

M11 remains extensible for future plate metadata.

---

## 45. Future Cross-Camera Re-ID

Cross-camera identity remains deferred.

Future:

```text
Camera A Track
      ↓
Global Vehicle ID
      ↓
Camera B Track
```

Do not fabricate a global ID now.

---

## 46. Acceptance Criteria

### Architecture
- [ ] Downstream-only from M10
- [ ] M1–M10 unchanged except reproducible integration fixes
- [ ] No new detection/tracking engine

### Clip
- [ ] Timestamp correctly mapped
- [ ] Pre-event context included
- [ ] Post-event context included
- [ ] Event inside clip
- [ ] Partial clips handled
- [ ] Maximum duration enforced

### Annotation
- [ ] Event marker
- [ ] Bounding box
- [ ] Track ID
- [ ] Camera ID
- [ ] Event type
- [ ] Spatial context where available
- [ ] Behavioral context where available
- [ ] Scene state where available

### Persistence
- [ ] MP4 persisted
- [ ] Thumbnail persisted
- [ ] Metadata persisted
- [ ] SQLite WAL used
- [ ] Database idempotency
- [ ] Restart recovery
- [ ] Missing artifact detection
- [ ] Orphan detection

### Reliability
- [ ] Bounded queue
- [ ] Queue-full behavior
- [ ] Retry behavior and backoff
- [ ] Source-unavailable behavior
- [ ] Partial live/RTSP buffer behavior
- [ ] Encoding failure isolation
- [ ] Encoder-unavailable graceful degradation
- [ ] Storage failure isolation
- [ ] Disk-space backpressure
- [ ] Alerts survive clip failure
- [ ] M6/M10 continue when M11 is unavailable

### Performance
- [ ] M6 critical path unaffected
- [ ] Asynchronous generation
- [ ] Bounded resource use
- [ ] Per-frame annotation cost measured
- [ ] Generation latency measured
- [ ] Storage measured

### Validation
- [ ] Unit tests
- [ ] Integration tests
- [ ] Failure tests
- [ ] Idempotency
- [ ] Recovery
- [ ] Daytime real-video
- [ ] Nighttime real-video
- [ ] Close-range real-video
- [ ] Visual inspection

---

## 47. Definition of Done

M11 is complete only when:

1. IncidentClip contract exists.
2. M11 consumes M10 EvidencePackages.
3. Event timestamps map correctly.
4. Pre-event footage is included.
5. Post-event footage is included.
6. Event frame is present.
7. Annotated clip is generated.
8. Thumbnail is generated.
9. Metadata is persisted.
10. Idempotency is database-enforced.
11. Queue is bounded.
12. Generation is asynchronous.
13. Source-unavailable handling works.
14. Partial clip handling works.
15. Encoding failure handling works.
16. Filesystem/DB ordering is correct.
17. Recovery/reconciliation works.
18. M6 critical path is unaffected.
19. Daytime test passes.
20. Nighttime test passes.
21. Close-range test passes.
22. Visual outputs are inspected.
23. M1–M10 regression tests pass.
24. Independent audit passes.
25. Completion report exists.

---

## 48. Required Completion Report

Create:

`milestone11_completion.md`

Include:

1. Summary
2. Architecture
3. Files/modules
4. IncidentClip contract
5. Lifecycle
6. Timestamp mapping
7. Clip-window configuration
8. Annotation
9. Thumbnail
10. Queue architecture
11. Queue-full behavior
12. Retry behavior
13. Encoding
14. Storage
15. SQLite
16. Idempotency
17. Recovery
18. Reconciliation
19. Failure handling
20. Daytime validation
21. Nighttime validation
22. Close-range validation
23. Visual evidence
24. Performance
25. Storage metrics
26. M6 regression
27. M10 regression
28. Limitations
29. Known issues
30. M12 integration
31. Acceptance table
32. Final status

---

## 49. Independent Cross-Verification

Before PASS, independently verify:

- contract
- timestamp mapping
- event-centered window
- frame accuracy
- pre/post duration
- partial behavior
- annotations
- thumbnail
- encoding
- persistence
- WAL
- UNIQUE constraint
- idempotency
- queue bounds
- queue-full behavior
- retries
- source failure
- encoding failure
- filesystem failure
- restart recovery
- orphan detection
- missing artifact detection
- resource bounds
- M6 regression
- M10 regression
- real-video demonstrations

The auditor must not modify implementation.

If a defect is found:

`M11 = FAIL`

Fix only the identified M11 defect and rerun the audit.

---

## 50. Freeze Rule

When M11 passes:

`M11 = PASS / FROZEN`

Do not begin M12 until:
- completion report exists
- independent audit exists
- visual demonstrations inspected
- acceptance criteria satisfied
- no critical defects remain

---

## 51. STOP CONDITION

After M11 implementation and validation:

**STOP.**

Do not begin M12, ANPR, cross-camera Re-ID, or dashboard implementation until M11 has been reviewed.

M11 failure must never become an M6/M10 system failure.

The following must continue even when M11 is unavailable:

```text
M6 SecurityEvents / Alerts
M10 Evidence Generation
```

---

## 52. Final Principle

M10 established:

> “We have visual evidence of the detected event.”

M11 extends this into:

> “We can show what happened immediately before, during, and after the event.”

The M11 foundation is:

**Event → Evidence → Incident Clip**

============================================================
END OF M11
============================================================
