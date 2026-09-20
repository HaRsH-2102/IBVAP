# IBVAP — Milestone 10 Specification
## Evidence & Event Intelligence

**Status:** SPECIFICATION / NOT STARTED  
**Upstream:** M1–M8 FROZEN  
**ANPR:** M9 DEFERRED  
**Next:** M11 — Evidence Video Clip Generation

---

## 1. Objective

Transform M6 security events into structured, persistent, visually inspectable evidence packages without modifying M1–M8.

M10 consumes existing M6 SecurityEvents, M7 behavioral context, M8 scene context, and relevant M4/M5 track/spatial information.

M10 does **not** perform new:
- detection
- tracking
- spatial analysis
- behavioral analysis
- ANPR
- Re-ID
- dashboard work

---

## 2. Architecture

```text
M3 Detection → M4 Tracking → M5 Spatial Events ─┐
                                                 ├→ M6 SecurityEvent
M7 Behavioral Events ───────────────────────────┤
M8 Scene State ──────────────────────────────────┘
                                                       ↓
                                                  M10 Evidence
                                                       ↓
                                               EvidencePackage
```

M1–M8 remain frozen. Any upstream deficiency must be documented rather than silently patched.

---

## 3. EvidencePackage Contract

Create `app/domain/evidence.py` containing a typed `EvidencePackage` with at least:

- `evidence_id`
- `security_event_id`
- `alert_id`
- `camera_id`
- `track_id`
- `event_type`
- `timestamp`
- `object_class`
- `bounding_box`
- `scene_state`
- `spatial_context`
- `behavioral_context`
- `trajectory_snapshot`
- `annotated_frame_reference`
- `metadata`
- `created_at`
- `status`
- `evidence_quality`

Optional data must remain optional; never fabricate missing information.

---

## 4. Evidence Status

Use an explicit status enum:

```text
PENDING
CAPTURED
PERSISTED
QUEUE_FAILED
CAPTURE_FAILED
STORAGE_FAILED
ARTIFACT_MISSING
UNAVAILABLE
```

Status transitions must be deterministic and persisted where applicable.

A failed evidence operation must never invalidate the originating SecurityEvent or Alert.

---

## 5. Evidence Contents

Each package should preserve:

- event-time frame
- immutable bounding-box snapshot
- track ID and camera ID
- object class
- bounded trajectory snapshot
- M5 spatial context when available
- M7 behavioral context when available
- M8 scene state when available
- original and annotated frame references
- evidence quality
- timestamp difference between requested and captured frame

Suggested trajectory default: **30 points**, configurable.

---

## 6. Frame Evidence

Capture the frame closest to the event timestamp.

Record:

- `requested_event_timestamp`
- `actual_frame_timestamp`
- `timestamp_delta_ms`
- `evidence_quality`

Evidence quality is determined using configurable thresholds:

```text
evidence_exact_tolerance_ms = 80
evidence_max_delta_ms = 500
```

Default classification:

```text
delta <= 80 ms
    → EXACT

80 ms < delta <= 500 ms
    → NEAREST_AVAILABLE

delta > 500 ms
    → UNAVAILABLE
```

These are starting defaults and must remain configurable.

If no usable frame exists, the SecurityEvent and Alert still remain valid.

---

## 7. Trajectory Snapshot Policy

The trajectory snapshot contains the **most recent N trajectory points** at evidence creation time.

Default:

```text
trajectory_snapshot_points = 30
```

Only the most recent N points are retained in the evidence package.

Do not store unlimited trajectory history.

The selected points must preserve their original:

- timestamp
- frame ID, when available
- position
- associated track context

---

## 8. Annotated Evidence

Generate an annotated copy without modifying the original.

The annotation should show, where available:

- camera ID
- timestamp
- event type
- track ID
- object class
- bounding box
- zone/line information

If shared NumPy/OpenCV frame data is used, copy it before annotation.

---

## 9. Original vs Annotated Evidence

The original frame is immutable.

The annotated frame is a derived artifact.

Never overwrite the original frame with annotations.

Suggested structure:

```text
evidence/
  <camera_id>/
    <date>/
      <evidence_id>/
        original.jpg
        annotated.jpg
        metadata.json
```

Use collision-safe IDs, preferably UUID4.

---

## 10. Evidence Repository

Create:

- `BaseEvidenceRepository`
- `LocalEvidenceRepository`

Required operations:

- `create_evidence()`
- `get_evidence()`
- `list_evidence_for_event()`
- `list_evidence_for_alert()`
- `update_evidence_status()`

Keep repository logic separate from domain logic.

---

## 11. SQLite Integration

Extend existing M6 persistence only as necessary.

Do not duplicate Alert/SecurityEvent schemas.

Suggested `evidence_packages` fields:

- evidence ID
- security event ID
- alert ID
- camera ID
- track ID
- event type
- timestamp
- evidence quality
- status
- original frame path
- annotated frame path
- metadata JSON
- created timestamp

### Database Idempotency Constraint

`security_event_id` must have a **UNIQUE database constraint**.

Application-level lookup may be used as an optimization, but the database constraint is the actual concurrency-safe idempotency guarantee.

The same SecurityEvent must not result in multiple identical EvidencePackages.

---

## 12. SQLite Concurrency

Because M6 processing and M10 evidence persistence may execute concurrently:

- Enable SQLite **WAL mode**.
- Configure a reasonable SQLite busy timeout.
- Prefer serialized evidence writes through the dedicated evidence worker.
- Do not use unsafe shared SQLite connections across threads.

The evidence worker must not recreate the synchronous M6 disk-I/O bottleneck on the critical event path.

---

## 13. Evidence Persistence Ordering

M10 uses two persistence targets:

1. Filesystem image artifacts
2. SQLite metadata

The required order is:

```text
SecurityEvent
      ↓
Evidence request
      ↓
Write original image
      ↓
Write annotated image
      ↓
Validate artifacts
      ↓
Commit SQLite evidence metadata
```

Never commit a database row referencing artifacts that have not successfully been written and validated.

### Crash Recovery States

On restart:

**DB row + all expected files**
→ `PERSISTED`

**DB row + missing file**
→ `ARTIFACT_MISSING`

**File(s) + no DB row**
→ `ORPHANED_ARTIFACT`

Orphaned artifacts must be detectable.

M10 must not silently delete orphaned artifacts during normal startup.

---

## 14. Asynchronous Evidence Worker

Evidence generation must not unnecessarily block M6 event processing.

Preferred flow:

```text
SecurityEvent
      ↓
bounded Evidence Queue
      ↓
Evidence Worker
      ↓
frame capture
      ↓
image annotation
      ↓
image encoding
      ↓
filesystem
      ↓
SQLite metadata
```

Suggested queue capacity:

`50`

This value is configurable.

---

## 15. Queue-Full Behavior

A full evidence queue must **never silently discard the SecurityEvent**.

If the queue is full:

1. Keep the SecurityEvent and Alert intact.
2. Create/retain an evidence request state of:
   `QUEUE_FAILED`
3. Record:
   `failure_reason = EVIDENCE_QUEUE_FULL`
4. Log the event with:
   - security event ID
   - alert ID
   - camera ID
   - track ID
5. Make the request retryable according to the configured retry policy.

A queue-full request is **not** a duplicate.

Suggested initial behavior:

```text
max_evidence_retries = 1
```

The retry policy must be configurable.

If the retry also fails, preserve the final failure state and do not block M6.

---

## 16. Idempotency and Retry Semantics

Idempotency is based on:

`security_event_id`

The database UNIQUE constraint is authoritative.

Example:

```text
Evidence request
      ↓
Worker failure
      ↓
Retry
      ↓
Existing evidence checked
      ↓
If already persisted → reuse existing package
If not persisted → retry safely
```

A failed request must not be interpreted as an already-completed request.

---

## 17. Configuration

All operational values must be configurable.

Suggested defaults:

```text
evidence_enabled = true
evidence_queue_capacity = 50
trajectory_snapshot_points = 30

evidence_exact_tolerance_ms = 80
evidence_max_delta_ms = 500

max_evidence_retries = 1

evidence_image_format = JPEG
evidence_image_quality = 90

evidence_retention_days = 30
```

---

## 18. Multi-Rule Handling

M6 may intentionally produce multiple SecurityEvents from one physical event.

Example:

```text
Generic Zone Entry Rule
        +
Restricted Zone Rule
        ↓
SecurityEvent A
SecurityEvent B
```

M10 must preserve each SecurityEvent separately.

Evidence artifacts may be physically shared when appropriate, but the SecurityEvent relationships must remain distinct.

---

## 19. Failure Isolation

Evidence failures must not crash or invalidate the alert pipeline.

Test:

- missing frame
- invalid/corrupt frame
- missing camera ID
- missing track ID
- missing bounding box
- filesystem permission failure
- disk write failure
- database unavailable
- queue overflow
- duplicate request
- restart

One camera/event failing must not stop other evidence processing.

---

## 20. Privacy and Security

M10 introduces no new biometric processing.

Do not implement:

- facial recognition
- face identification
- demographic classification
- identity inference

Evidence paths should not be unnecessarily exposed through logs or public directories.

---

## 21. Evidence Retention and Reconciliation

Suggested retention metadata:

`evidence_retention_days = 30`

Actual automatic deletion is optional for M10.

The authoritative relationship is:

```text
SecurityEvent / Alert
        ↓
Evidence metadata
        ↓
Artifact files
```

If an artifact is removed while its DB row remains:

`status = ARTIFACT_MISSING`

If a file exists without a DB row:

`status = ORPHANED_ARTIFACT` for reconciliation reporting.

Retention cleanup must never cascade-delete SecurityEvents or Alerts.

M10 should not automatically delete orphaned artifacts unless explicitly configured.

---

## 22. M6 / M7 / M8 Integration

M10 consumes M6 SecurityEvents and preserves relevant M5/M7/M8 context.

It must not rerun or modify those engines.

Example:

```text
event_type = LOITERING
behavior_duration = 12.4
zone_id = restricted_zone_01
scene_state = NIGHT
```

If information is unavailable, record it as unavailable rather than guessing.

---

## 23. Explicit Non-Goals

M10 MUST NOT implement:

- ANPR/OCR
- vehicle Re-ID
- cross-camera identity
- global vehicle IDs
- video clips
- video encoding
- dashboard UI
- command center
- maps
- new detection/tracking models
- advanced correlation
- predictive analytics

ANPR remains deferred.

Cross-camera Re-ID remains deferred.

---

## 24. Files / Modules

Suggested structure:

```text
app/domain/evidence.py

app/evidence/
    __init__.py
    evidence_service.py
    evidence_worker.py
    evidence_renderer.py
    evidence_repository.py

app/infrastructure/evidence_storage.py

tests/
    test_evidence_domain.py
    test_evidence_renderer.py
    test_evidence_service.py
    test_evidence_failure.py
    test_evidence_integration.py
    test_evidence_idempotency.py
    test_evidence_recovery.py
    run_m10_evidence.py
```

Follow existing project conventions where appropriate.

---

## 25. Testing Strategy

Create tests for:

### Test A — Evidence Domain

Verify:

- required fields
- serialization
- unique evidence IDs
- status transitions
- optional field handling

### Test B — Frame Capture

Trigger a known event and verify the corresponding frame is captured.

### Test C — Evidence Quality

Test exact, nearest, and unavailable timestamps against the configured thresholds.

### Test D — Annotation

Verify:

- bounding box
- track ID
- event text
- original image remains unchanged

### Test E — Spatial Event

Verify a `ZONE_ENTER` evidence package contains:

- zone ID
- track ID
- bounding box
- trajectory
- timestamp

### Test F — Behavioral Event

Verify `LOITERING` evidence contains:

- behavior type
- duration
- track
- frame
- timestamp

### Test G — Night Event

Run on the night video and verify M8-provided:

`scene_state = NIGHT`

M10 must not independently infer it.

### Test H — Multiple Alerts

Generate two alerts from the same physical event and verify both remain distinct.

### Test I — Queue Full

Force queue saturation and verify:

- SecurityEvent survives
- Alert survives
- evidence status becomes `QUEUE_FAILED`
- failure reason is recorded
- request is retryable
- no silent loss occurs

### Test J — Filesystem/DB Crash Ordering

Simulate:

- file write failure
- DB write failure after successful file writes
- restart during recovery

Verify no invalid DB reference is committed.

### Test K — Orphan Reconciliation

Test:

- DB row + missing file
- file + missing DB row
- complete DB + file pair

### Test L — Restart

Restart after evidence creation and verify evidence metadata and stored paths remain valid.

### Test M — Idempotency Race

Submit concurrent requests for the same SecurityEvent and verify the database UNIQUE constraint prevents duplicate EvidencePackages.

---

## 26. Real-Video Validation

Validation MUST be visible, not only internal.

Test at least:

1. Daytime traffic
2. Night traffic
3. Close-range traffic

Do not hardcode developer-specific absolute paths.

Use:

`IBVAP_TEST_VIDEO`

when appropriate, or repository-relative paths.

Save results under:

```text
artifacts/m10/
    daytime/
    nighttime/
    close_range/
    metadata/
    failures/
```

---

## 27. Required Visual Demonstration

The validation harness must visibly show:

```text
Original Frame
      +
Annotated Frame
      +
Event Details
```

For every selected evidence sample, the reviewer must be able to inspect:

- original image
- annotated image
- event type
- timestamp
- camera ID
- track ID
- object class
- spatial context
- behavioral context
- scene state
- evidence status

M10 MUST NOT be declared validated solely from terminal logs.

---

## 28. Performance Targets

Measure separately:

- evidence queue wait time
- frame-copy latency
- annotation latency
- image encode latency
- filesystem write latency
- SQLite write latency
- total asynchronous evidence latency
- queue depth
- queue failure count
- storage failure count

Target synchronous evidence preparation overhead:

`< 2 ms`

Disk I/O may take longer because it is outside the critical event path.

Report:

```text
Critical event-path latency
vs.
Asynchronous evidence latency
```

Do not combine them into a misleading single metric.

---

## 29. Memory and Backpressure

All queues must be bounded.

Do not retain unlimited frames.

Do not maintain a global list of all evidence images.

Release evidence references after persistence.

The worker must not hold more than the configured queue plus its currently processing item.

---

## 30. Error Isolation

Failure for one evidence package must not stop other evidence packages.

For example:

```text
Camera A evidence failure
        ↓
Camera B continues normally
```

Errors must include:

- evidence ID
- security event ID
- camera ID
- track ID
- failure reason

---

## 31. Multi-Camera Isolation

M10 must preserve camera boundaries.

Evidence identity must include:

`camera_id`

Track IDs remain camera-local.

M10 MUST NOT implement global vehicle identity.

---

## 32. Evidence Naming

Use collision-safe names.

Never use generic names such as:

- `frame.jpg`
- `alert.jpg`

Recommended:

```text
<evidence_id>_original.jpg
<evidence_id>_annotated.jpg
<evidence_id>.json
```

---

## 33. Logging

Log:

- evidence requested
- evidence captured
- evidence annotated
- evidence persisted
- evidence failed
- queue full
- recovery reconciliation
- orphan detection

Include:

- evidence ID
- security event ID
- camera ID
- track ID

Avoid logging raw image bytes or unnecessary sensitive content.

---

## 34. Testing Output

The validation script must generate:

- source video
- source FPS
- events observed
- evidence packages created
- evidence statuses
- evidence failures
- average evidence preparation latency
- maximum evidence preparation latency
- queue depth
- queue failures
- storage failures
- missing-frame count
- reconciliation results

It must also produce visible evidence artifacts.

Suggested:

```text
artifacts/m10/
    report.md
    daytime/
        event_001_original.jpg
        event_001_annotated.jpg
        event_001.json
```

---

## 35. Required Visual Demonstration Events

Demonstrate, when naturally available:

- `ZONE_ENTER`
- `ZONE_EXIT`
- `LINE_CROSS`
- `LOITERING`
- `RESTRICTED_ZONE_DWELL`
- a `NIGHT` event

If an event cannot be reproduced in selected real footage, document:

`NOT OBSERVED IN SELECTED VIDEO`

A deterministic synthetic event may be used for that specific unit/integration test.

Do not fabricate real-video observations.

---

## 36. Benchmark Video Policy

Reuse established canonical videos.

Do not hardcode developer-specific absolute paths.

Use:

`IBVAP_TEST_VIDEO`

when an environment override is appropriate.

Otherwise resolve repository-relative paths.

---

## 37. Licensing / Dependencies

Any newly introduced dependency must record:

- package name
- version
- license

Do not add dependencies solely for convenience when existing dependencies or the standard library are sufficient.

---

## 38. M11 Integration

M11 will consume:

`EvidencePackage`

and extend it with:

- pre-event video
- event video
- post-event video

The M10 evidence timestamp becomes the anchor for M11 clip generation.

M10 does not generate clips.

---

## 39. Future Dashboard Integration

M12 should eventually consume M10 through:

```text
EvidenceRepository
      ↓
Evidence API
      ↓
Command Center
```

The future dashboard can display:

- event
- timestamp
- camera
- track
- object
- scene
- spatial context
- behavior
- annotated frame
- incident clip

M10 remains UI-independent.

---

## 40. Future ANPR Integration

ANPR remains deferred.

When M9 is revisited:

```text
ANPREvent
      ↓
M6 SecurityEvent
      ↓
M10 EvidencePackage
```

Future evidence may contain:

- `plate_text`
- `plate_confidence`
- `plate_crop_reference`

M10 must be extensible enough to accept these later.

---

## 41. Future Cross-Camera Re-ID

Cross-camera Re-ID is deferred.

When implemented:

```text
Camera A Track
      ↓
Global Vehicle ID
      ↓
Camera B Track
```

M10 evidence packages may eventually contain `global_vehicle_id`.

This field must NOT be fabricated now.

---

## 42. Acceptance Criteria

### Architecture

- [ ] M1–M8 unchanged
- [ ] M9 remains deferred
- [ ] Evidence layer is downstream-only

### Evidence

- [ ] EvidencePackage exists
- [ ] SecurityEvents produce evidence
- [ ] Bounding boxes preserved
- [ ] Track information preserved
- [ ] Most-recent trajectory snapshot preserved
- [ ] Spatial context preserved
- [ ] Behavioral context preserved
- [ ] Scene context preserved when available

### Evidence Quality

- [ ] Exact tolerance configurable
- [ ] Maximum timestamp delta configurable
- [ ] EXACT / NEAREST_AVAILABLE / UNAVAILABLE deterministic

### Visual Evidence

- [ ] Original frame saved
- [ ] Annotated frame saved
- [ ] Bounding box visibly correct
- [ ] Event metadata visibly correct

### Persistence

- [ ] Files written before DB metadata commit
- [ ] SQLite WAL enabled
- [ ] UNIQUE SecurityEvent constraint enforced
- [ ] Restart recovery works
- [ ] Missing artifacts detectable
- [ ] Orphaned files detectable

### Reliability

- [ ] Evidence failure does not delete alerts
- [ ] Evidence failure does not crash pipeline
- [ ] Queue is bounded
- [ ] Queue-full behavior is explicit
- [ ] Retry behavior is explicit
- [ ] Duplicate evidence prevented
- [ ] Camera isolation preserved

### Performance

- [ ] Synchronous preparation meets target
- [ ] Disk I/O does not block critical event path
- [ ] Queue depth measured
- [ ] No unbounded memory growth

### Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Failure tests pass
- [ ] Idempotency race test passes
- [ ] Recovery/reconciliation tests pass
- [ ] Daytime real-video test
- [ ] Nighttime real-video test
- [ ] Close-range real-video test
- [ ] Visual results manually inspected

---

## 43. Definition of Done

M10 is complete only when:

1. EvidencePackage contract exists.
2. EvidenceService consumes M6 SecurityEvents.
3. Actual frames are captured.
4. Original frames are preserved.
5. Annotated evidence frames are generated.
6. Track/bounding-box information is preserved.
7. Spatial context is preserved.
8. Behavioral context is preserved.
9. Scene context is preserved.
10. Evidence quality thresholds are deterministic.
11. Evidence status is explicit.
12. Evidence metadata is persisted.
13. Evidence files are persisted before DB commit.
14. SQLite concurrency is safely configured.
15. Database-level idempotency is enforced.
16. Evidence generation is asynchronous/bounded.
17. Queue-full behavior is explicit and retryable.
18. Evidence failures do not destroy alerts.
19. Duplicate evidence is prevented.
20. Restart/reconciliation behavior is validated.
21. Daytime video is visibly tested.
22. Nighttime video is visibly tested.
23. Close-range video is visibly tested.
24. Performance is measured.
25. No frozen upstream milestone is modified.
26. A complete M10 completion report is produced.
27. An independent audit is passed.

---

## 44. Required Completion Report

After implementation, create:

`milestone10_completion.md`

It must contain:

1. Summary
2. Architecture
3. Files changed
4. Evidence contract
5. Status lifecycle
6. Evidence quality thresholds
7. Evidence generation flow
8. Queue-full behavior
9. Retry behavior
10. Storage design
11. Filesystem/DB ordering
12. SQLite concurrency configuration
13. Persistence design
14. Idempotency enforcement
15. Recovery/reconciliation
16. Failure handling
17. Visual validation
18. Daytime results
19. Nighttime results
20. Close-range results
21. Performance
22. Queue behavior
23. Storage statistics
24. M6 regression check
25. M7 regression check
26. M8 regression check
27. Limitations
28. Known issues
29. Future M11 integration
30. Acceptance criteria table
31. Final status

---

## 45. Independent Cross-Verification

Before declaring PASS, run an independent audit.

Verify:

- EvidencePackage fields
- status lifecycle
- SecurityEvent relationship
- frame correctness
- bounding-box correctness
- track correctness
- timestamp correctness
- evidence-quality classification
- original/annotated separation
- filesystem/DB ordering
- SQLite concurrency
- UNIQUE constraint
- idempotency race behavior
- persistence
- restart recovery
- orphan detection
- missing-artifact detection
- duplicate prevention
- queue-full behavior
- retry behavior
- failure isolation
- queue bounds
- memory behavior
- real-video results
- upstream regression

The auditor must not modify the implementation.

If defects are found:

`M10 = FAIL`

Fix only identified M10 defects and re-run the audit.

---

## 46. Freeze Rule

When M10 passes:

`M10 = PASS / FROZEN`

Do not proceed to M11 until:

- completion report exists
- independent audit exists
- acceptance criteria are satisfied
- visual validation has been inspected
- no known critical defects remain

---

## 47. STOP CONDITION

After M10 is implemented and validated:

**STOP.**

Do not begin:

- M11
- M12
- Re-ID
- ANPR
- Dashboard

until the M10 completion report has been reviewed.

The next milestone after a successful M10 freeze is:

**M11 — Evidence Video Clip Generation**

---

## 48. Final Principle

M10 changes IBVAP from:

> “The AI detected something.”

into:

> “The system detected something, knows why it is suspicious, knows where and when it happened, knows which tracked object was involved, and can provide visual evidence proving the event.”

That evidence foundation becomes the basis for:

- M11 → Incident video clips
- M12 → Command Center
- later milestones → Multi-camera intelligence
- final ANPR integration

M10 must remain focused on evidence.

============================================================
END OF M10
============================================================
