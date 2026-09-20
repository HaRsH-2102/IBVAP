# IBVAP — Milestone 5
## Spatial Intelligence — Zones, Virtual Fences & Tripwires

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Development agent:** Google Antigravity  
**Milestone:** 5 — Spatial Intelligence Layer  
**Prerequisites:** M1, M2, M3, and M4 completed and validated  
**Current detector baseline:** YOLOv8n, RTX 4060, batch size 1, 1280×1280, confidence 0.25  
**Current tracker:** ByteTrack  
**Primary benchmark:** canonical `videoplayback.mp4` test asset

**Benchmark-path policy:** Do not hardcode a personal absolute path. The canonical video should be referenced through a shared test-asset configuration, preferably `IBVAP_TEST_VIDEO`, with a repository-relative default such as `tests/assets/videoplayback.mp4` when the asset is available locally.

---

## 1. Purpose

Milestone 4 established persistent temporal identities:

```text
Detection[]
    ↓
ByteTrack
    ↓
Track[]
```

Milestone 5 adds **spatial intelligence**.

The system must understand where a tracked object is relative to configurable geometric regions and boundaries in a camera view.

```text
Video
  ↓
M2 Ingestion
  ↓
Frame
  ↓
M3 Detection
  ↓
Detection[]
  ↓
M4 Tracking
  ↓
Track[]
  ↓
M5 Spatial Intelligence
  ↓
SpatialEvent[]
```

M5 answers:

> **Where is this tracked object, and what spatial relationship does it have with configured regions or boundaries?**

Examples:

```text
Track 17 → inside Restricted Zone
Track 23 → crossed Virtual Fence 1
Track 31 → entered Zone A
```

M5 must **not** decide whether an event is a security incident or generate alerts. That belongs to the future event/alert layer.

---

## 2. Critical Scope Rule

M5 is ONLY the geometric/spatial reasoning layer.

Implement:

- camera coordinate space
- configurable zones
- configurable lines/tripwires
- point-in-polygon tests
- line-crossing tests
- entry detection
- exit detection
- zone occupancy state
- spatial event objects
- spatial configuration validation
- spatial visualization for testing

Do NOT implement:

- alert generation
- alarm escalation
- suspicious activity
- loitering
- behavioral classification
- risk scoring
- ANPR
- OCR
- face recognition
- night movement detection
- cross-camera identity
- command-and-control integration
- notifications
- production dashboard
- automatic incident severity
- GPS/geographic mapping

M5 produces **geometric facts**. Future milestones decide what those facts mean operationally.

---

## 3. Core Design Principle

Keep this separation:

```text
M4
Track[]
   ↓
M5
Spatial reasoning
   ↓
SpatialEvent[]
   ↓
Future M6
Security/Event interpretation
   ↓
Alert/Event
```

For example:

### M5

```text
Track 17 crossed Fence A
```

### Future M6

```text
Fence A = restricted boundary
+
Track 17 = person
+
crossing direction = outside → inside
↓
Security intrusion event
```

Do not combine these layers prematurely.

---

## 4. First Action — Inspect Existing Architecture

Before implementation, inspect:

1. M1 domain contracts.
2. M2 Frame and camera/source handling.
3. M3 Detection and bounding-box conventions.
4. M4 Track.
5. M4 trajectory history.
6. `camera_id` semantics.
7. Existing configuration infrastructure.
8. Existing logging/metrics.
9. Existing tests.
10. Existing visualization utilities.

Do not rewrite M1–M4.

M5 must consume the existing `Track[]`.

---

## 5. Coordinate System

Use a clearly defined camera-image coordinate system:

```text
(0,0)
  ┌──────────────────────────────→ X
  │
  │
  │
  ↓
  Y
```

Therefore:

- origin = top-left
- X increases right
- Y increases downward
- coordinates are pixel coordinates
- geometry is camera-specific

Do not use normalized coordinates internally unless clearly justified.

---

## 6. Camera-Specific Geometry

Every camera has a different viewpoint.

Therefore:

```text
CAM01
  ├── Zone A
  ├── Zone B
  └── Fence 1

CAM02
  ├── Zone A
  └── Fence 1
```

must be independent configurations.

A polygon configured for CAM01 must never apply to CAM02.

Always resolve:

```text
camera_id
    ↓
camera-specific spatial configuration
```

---

## 7. Spatial Configuration Model

Create a configurable spatial configuration model.

Conceptually:

```text
CameraSpatialConfig
├── camera_id
├── zones[]
└── lines[]
```

Zone:

```text
Zone
├── id
├── name
├── polygon
└── enabled
```

Tripwire:

```text
Tripwire
├── id
├── name
├── start_point
├── end_point
└── enabled
```

Optional metadata may include description, object classes of interest, and visualization settings.

Do not add security severity yet.

---

## 8. Polygon / Zone Representation

A zone is a polygon in image coordinates.

Support:

- triangle
- rectangle
- arbitrary simple polygon
- concave polygons

Validate that a polygon has enough points to form a valid region.

---

## 9. Zone Semantics

A zone answers:

> Is the tracked object currently inside this polygon?

Conceptually:

```text
Track
  ↓
reference point
  ↓
point-in-polygon
  ↓
INSIDE / OUTSIDE
```

Do not infer physical-world distance from image coordinates.

---

## 10. Track Reference Point

Support an explicit reference-point policy.

Initial policy:

### Bottom-center of bounding box

```text
        ┌──────────────┐
        │    CAR       │
        │              │
        └──────●───────┘
               ↑
         bottom center
```

The bottom-center is often a better approximation of ground contact for people and vehicles than the geometric center.

Retain the track centroid for trajectory visualization and future analysis.

Document which reference point is used for each spatial operation.

---

## 11. Point-in-Polygon

Implement a robust point-in-polygon operation.

Use a reliable geometry implementation rather than fragile custom math unless there is a strong reason.

Define deterministic boundary behavior, for example:

> A point exactly on a zone boundary is treated as inside.

Whatever policy is selected must be documented and tested.

---

## 12. Zone Entry

A zone entry occurs when:

```text
Previous state = OUTSIDE
Current state  = INSIDE
```

Then:

```text
ZONE_ENTER
```

must be generated once.

Do not emit an entry event every frame while the object remains inside.

---

## 13. Zone Exit

A zone exit occurs when:

```text
Previous state = INSIDE
Current state  = OUTSIDE
```

Then:

```text
ZONE_EXIT
```

must be generated once.

Do not generate repeated exits.

---

## 14. Zone Occupancy

While a track remains inside:

```text
Track 17
Zone A
State = INSIDE
```

The spatial engine may maintain:

- first-entry timestamp
- latest observed timestamp
- current duration

Do NOT classify long occupancy as loitering. That belongs to a future behavioral milestone.

---

## 15. Tripwire / Virtual Fence

A tripwire is a line segment:

```text
P1 ●────────────────● P2
```

A track trajectory may cross it:

```text
              Track
                ↓
                ●
                │
P1 ●────────────X────────────● P2
                │
                ●
```

The geometry engine must detect the crossing.

---

## 16. Line-Crossing Detection

Use trajectory movement:

```text
previous reference point → P_prev
current reference point  → P_curr

tripwire
────────────────────────────

Does segment P_prev → P_curr intersect the tripwire?
```

If yes:

```text
LINE_CROSS
```

Do not trigger based only on current position.

---

## 17. Crossing Direction

For a directed tripwire, calculate direction.

Possible semantic result:

```text
A_TO_B
```

or:

```text
B_TO_A
```

Direction must be defined by the camera configuration.

Do not globally hard-code "entering border" because every camera viewpoint differs.

---

## 18. Duplicate Crossing Prevention and Hysteresis

An object may remain near a line for several frames, and real bounding-box trajectories contain small amounts of jitter.

Do not produce repeated crossing events for one physical crossing.

Use a **state-based crossing detector with configurable hysteresis**, rather than a simple per-frame intersection test.

Initial engineering default:

```text
crossing_epsilon = 3 pixels
```

at the canonical 1280×1280 inference/reference resolution.

This value must be configurable and validated with real trajectories. The implementation may propose a better default after testing, but must document the reason.

Define three conceptual states:

```text
SIDE_A
CROSSING_ZONE
SIDE_B
```

A valid crossing should require movement from one side beyond the epsilon boundary to the opposite side beyond the epsilon boundary.

Small oscillations such as:

```text
SIDE_A
  ↓
CROSSING_ZONE
  ↓
SIDE_A
```

must NOT generate a crossing event.

After a crossing:

```text
SIDE_A
  ↓
CROSSING_ZONE
  ↓
SIDE_B
  ↓
LINE_CROSS
```

the same track must move sufficiently away from the line before another opposite-direction crossing can be generated.

Do not use an arbitrary time-only cooldown as the primary correctness mechanism. A spatial/state-based hysteresis mechanism is preferred because it adapts to different object speeds.

### Near-parallel motion

A trajectory that remains on the same side of the line must not count as a crossing, even if it passes within the epsilon corridor.

The system must evaluate signed distance to the directed line and not rely only on approximate floating-point segment intersection.

Test and document the selected epsilon/tolerance behavior.

---

## 19. Track Lifecycle Interaction

If:

```text
Track 17
 ↓
Inside Zone A
 ↓
Track LOST
```

do NOT automatically emit:

```text
ZONE_EXIT
```

A missing object is not automatically outside the zone.

Distinguish:

```text
TRACK_LOST
```

from:

```text
ZONE_EXIT
```

Track lifecycle belongs to M4.

---

## 20. Track Reappearance

If a track reappears with the same M4 track ID:

```text
Track 17
LOST
 ↓
reappears
 ↓
Track 17
```

continue using the same spatial context where valid.

If M4 creates a new track ID, M5 treats it as a new identity.

Do not reconstruct identities in M5.

---

## 21. Spatial Event Model

Create:

```text
SpatialEvent
├── event_id
├── camera_id
├── track_id
├── event_type
├── spatial_object_id
├── timestamp
├── reference_point
└── metadata
```

Allowed event types:

```text
ZONE_ENTER
ZONE_EXIT
LINE_CROSS
```

Do not add `INTRUSION`, `SUSPICIOUS`, `THREAT`, or `ALARM`.

---

## 22. Event Traceability and Ordering

Every spatial event must be traceable to:

```text
camera
+
track
+
zone/line
+
timestamp
+
geometry state
```

Where the existing Track/Frame contracts provide a frame identifier, include it as optional event metadata or a first-class field.

This will let M6 interpret events without repeating geometry calculations.

### Event ordering

Multiple tracks may trigger events on the same frame. M5 must not depend on incidental Python dictionary/set iteration order.

Within one processing cycle, produce a deterministic ordering, preferably:

```text
timestamp
→ frame_id when available
→ camera_id
→ track_id
→ spatial_object_id
→ event_type
```

M6 may later apply its own semantic ordering or correlation rules.

---

## 23. Spatial Engine Abstraction

Create a dedicated spatial engine.

Conceptually:

```text
BaseSpatialEngine
        ↓
SpatialEngine
```

It consumes:

```text
Track[]
+
CameraSpatialConfig
```

and produces:

```text
SpatialEvent[]
```

It must not call YOLO or ByteTrack.

---

## 24. Processing Model

Expected flow:

```text
Frame
 ↓
Detector
 ↓
Detection[]
 ↓
Tracker
 ↓
Track[]
 ↓
SpatialEngine
 ↓
SpatialEvent[]
```

M5 operates on tracks.

---

## 25. Per-Camera State

Spatial state must be isolated:

```text
CAM01
 ├── zones
 ├── tripwires
 └── track spatial states

CAM02
 ├── zones
 ├── tripwires
 └── track spatial states
```

No cross-camera geometry.

---

## 26. Configuration Persistence

Initial M5 may use a human-readable configuration file.

Do not build a full database-backed configuration system yet.

Configuration should be:

- human-readable
- versionable
- camera-specific
- validated at startup

---

## 27. Zone Editing

No polished drawing UI is required.

Support manually defined coordinates first.

A future frontend can provide interactive polygon drawing.

---

## 28. Visualization

Create a technical spatial-validation view showing:

- camera frame
- tracked boxes
- track IDs
- trajectories
- configured zones
- zone labels
- tripwire lines
- spatial event indicators
- current spatial state

Do not build a production command-center dashboard.

---

## 29. Visualization Must Not Affect Benchmarks

Use:

### Clean benchmark
No visualization.

### Spatial validation
Visualization enabled.

Never mix the performance numbers.

---

## 30. Real Video Validation

Use the **canonical benchmark asset**:

```text
tests/assets/videoplayback.mp4
```

when the repository contains the test asset.

Allow the path to be overridden through:

```text
IBVAP_TEST_VIDEO
```

The implementation must resolve the test video through configuration/environment rather than embedding a developer-specific absolute path.

The benchmark asset should be the same canonical traffic video used in M3/M4 so performance and behavior can be compared across milestones.

This is a traffic video, not a real border scene.

Use it to validate:

- tracking continuity
- zone geometry
- line crossing
- spatial event generation

Do not make claims that this represents actual border-security conditions.

---

## 31. Synthetic Spatial Configurations

Because the traffic video is not a border camera, create synthetic test zones/lines that deliberately exercise the geometry.

Examples:

- polygon over part of the road
- tripwire across a traffic lane
- multiple independent zones

The purpose is geometric validation, not artificial security claims.

---

## 32. Deterministic Geometry Tests

Test known:

```text
inside
outside
boundary
```

points.

Test:

- rectangle
- triangle
- irregular polygon
- concave polygon where supported

---

## 33. Zone Entry Test

Create a zone a tracked object crosses:

```text
OUTSIDE
 ↓
INSIDE
 ↓
ZONE_ENTER
```

Exactly one entry event should be generated.

---

## 34. Zone Exit Test

Verify:

```text
INSIDE
 ↓
OUTSIDE
 ↓
ZONE_EXIT
```

Exactly one exit event.

---

## 35. Persistent Occupancy Test

Keep an object inside for multiple frames:

```text
ZONE_ENTER
INSIDE
INSIDE
INSIDE
```

Only one entry event should occur.

---

## 36. Tripwire Crossing Test

Use a known trajectory crossing a line.

Verify exactly one:

```text
LINE_CROSS
```

---

## 37. Reverse Crossing Test

Cross the same directional tripwire in the opposite direction.

Verify the direction reverses correctly.

---

## 38. Parallel Motion Test

Move an object parallel to the line without crossing.

Verify:

```text
LINE_CROSS = false
```

This is an important false-positive test.

---

## 39. Multiple Object Test

Verify independent spatial state:

```text
Track 1 → Zone A
Track 2 → Outside
Track 3 → Zone B
```

---

## 40. Multiple Camera Test

If a second synthetic camera context is available, verify:

```text
CAM01 Zone A
≠
CAM02 Zone A
```

No cross-camera contamination.

---

## 41. Lost Track Test

Test:

```text
Track inside zone
 ↓
Track LOST
```

M5 must NOT emit `ZONE_EXIT` merely because the track became temporarily unavailable.

---

## 42. Reappearance Test

A track that returns with the same M4 ID should continue its spatial state correctly.

---

## 43. Full Pipeline Test

Run:

```text
videoplayback.mp4
 ↓
M2
 ↓
M3
 ↓
M4
 ↓
M5
```

Verify:

- tracks remain correct
- zones render correctly
- tripwires render correctly
- transitions are correct
- crossing events are correct
- no crashes
- M5 does not become a bottleneck

---

## 44. Performance Metrics

Measure:

### M3
- detector FPS
- detector latency

### M4
- tracker latency

### M5
- spatial-engine latency
- geometry operations per frame
- spatial events per second

### End-to-end
- frame → detection → tracking → spatial reasoning latency
- end-to-end FPS
- dropped frames

Spatial processing should be substantially cheaper than neural inference.

---

## 45. Performance Target

Measure rather than fabricate.

Practical guideline:

- low-single-digit millisecond spatial processing is healthy
- large sustained latency increases require investigation
- no unbounded queues
- M2 live-edge behavior must remain intact

Profile before optimizing.

---

## 46. Accuracy Evaluation

Do not report generic "spatial accuracy = 99%" without ground truth.

Report:

- known-point tests
- transition correctness
- line-crossing correctness
- false positives
- false negatives
- boundary behavior
- qualitative real-video observations

---

## 47. Boundary Conditions and Crossing Tolerance

Test:

```text
inside
outside
exactly on boundary
very close to boundary
```

For tripwires:

```text
exactly on line
parallel
touching without crossing
crossing
```

Define deterministic behavior.

For line-crossing, explicitly validate the configured `crossing_epsilon`.

At the canonical 1280×1280 resolution, start with:

```text
3 px
```

unless testing demonstrates that another value is more appropriate.

The epsilon must be:

- configurable
- documented
- applied consistently
- tested with near-line jitter
- tested with genuinely crossing trajectories
- tested with parallel trajectories

Do not silently change the epsilon between benchmarks.

---

## 48. Reference-Point Noise

Bounding boxes may jitter.

Avoid repeated false events from tiny coordinate fluctuations.

Do not add complex smoothing unless testing demonstrates a problem.

If hysteresis/filtering is needed:

- document it
- make it configurable
- validate it

---

## 49. Spatial Object IDs

Zone/tripwire IDs must be unique within a camera.

Example:

```text
CAM01
 ├── zone: restricted_01
 ├── zone: restricted_02
 ├── line: fence_01
 └── line: gate_01
```

Events reference the exact spatial object.

---

## 50. Configuration Validation

Validate at startup:

- camera ID
- unique zone IDs
- unique tripwire IDs
- polygon point count
- polygon coordinates
- line endpoints
- enabled flags
- geometry validity

Fail clearly on invalid configuration.

---

## 51. Error Handling

Handle:

- missing camera configuration
- invalid polygon
- invalid line
- unknown track camera
- malformed track geometry
- empty track list
- engine initialization failure

`Track[] = []` is valid and should produce no events.

---

## 52. Event De-duplication

A state transition should produce one logical event.

For example:

```text
Track 17 + Zone A + OUTSIDE→INSIDE
```

produces one `ZONE_ENTER`, not one per frame.

---

## 53. Event History

Do not retain unlimited events.

A bounded recent-event buffer may be used for debugging.

Permanent persistence belongs to a later milestone.

---

## 54. No Alerting Yet

M5 may produce:

```text
ZONE_ENTER
ZONE_EXIT
LINE_CROSS
```

but must NOT produce:

```text
ALERT
INTRUSION
THREAT
SUSPICIOUS PERSON
```

Event interpretation comes later.

---

## 55. Dependencies and Licensing

Prefer mature geometry libraries where appropriate.

For every newly introduced dependency, record:

- package
- exact version
- license
- purpose
- whether it is runtime or development-only

The same dependency/license discipline used here should also be applied retroactively to the M3 documentation, especially for the Ultralytics/YOLO dependency and model version.

Record the exact Ultralytics version and its applicable license in the M3 project documentation. Do not assume that the license of the original ByteTrack research implementation automatically determines the license of the installed Ultralytics implementation.

Record:

- package
- exact version
- license
- purpose

Do not add large GIS frameworks because M5 uses image coordinates, not GPS coordinates.

---

## 56. Testing Discipline

For geometry operations:

1. deterministic unit test
2. edge-case test
3. actual Track-coordinate test
4. real-video test
5. visualization inspection

Do not rely only on visual inspection.

---

## 57. Acceptance Criteria

M5 is complete only when:

### Architecture
- spatial engine is separate from detector/tracker
- M4 `Track[]` is consumed
- camera-specific configuration exists
- spatial event contract exists

### Zones
- polygon zones supported
- point-in-polygon works
- entry works
- exit works
- occupancy state works
- duplicate transitions are suppressed

### Tripwires
- line segments supported
- crossing works
- direction works where configured
- parallel movement does not trigger
- near-parallel/jitter movement does not falsely trigger
- configurable crossing epsilon exists
- hysteresis/state logic prevents boundary bouncing from duplicating events
- duplicate crossings are suppressed

### Geometry
- coordinate system documented
- boundary behavior deterministic
- bottom-center reference point supported
- trajectory coordinates correct

### Lifecycle
- lost tracks do not falsely create exits
- reappearance with same ID preserves spatial state
- removed tracks clean up spatial state

### Multi-camera
- configurations are isolated

### Performance
- spatial latency measured
- end-to-end latency measured
- dropped frames measured
- memory stable

### Validation
- geometry tests pass
- real traffic video tested
- visualization correct
- edge cases documented

### Scope
No alerts, ANPR, face recognition, behavior analytics, or suspicious-activity classification.

---

## 58. Definition of Done

M5 is complete when:

1. Spatial engine abstraction exists.
2. Camera-specific configuration exists.
3. Zone model exists.
4. Tripwire model exists.
5. Spatial event model exists.
6. Coordinate system is documented.
7. Reference-point policy is implemented.
8. Point-in-polygon is implemented and tested.
9. Zone entry works.
10. Zone exit works.
11. Occupancy works.
12. Duplicate transitions are suppressed.
13. Line crossing works.
14. Directional crossing works where configured.
15. Configurable crossing epsilon exists.
16. Hysteresis/state logic prevents boundary bouncing.
17. Parallel and near-parallel movement does not trigger falsely.
18. Boundary behavior is deterministic.
19. Lost tracks do not falsely create exits.
20. Reappearance is handled.
21. Multiple tracks work independently.
22. Camera configurations are isolated.
23. Configuration validation exists.
24. Spatial event traceability exists.
25. Deterministic event ordering exists.
26. Event history is bounded if retained.
27. Clean benchmark mode exists.
28. Spatial visualization exists.
29. The canonical `videoplayback.mp4` asset is tested through configurable path resolution.
30. Spatial latency is measured.
31. End-to-end performance is measured.
32. Crossing epsilon/hysteresis is validated.
33. Tests pass.
34. No M6 alerting logic exists.
35. Antigravity stops after M5.

---

## 59. Required Final Report

After implementation, STOP and provide:

### 1. Summary
What was implemented?

### 2. Architecture
Explain:

```text
Track[]
   ↓
SpatialEngine
   ↓
SpatialEvent[]
```

### 3. Configuration
Explain the camera/zone/tripwire structure.

### 4. Geometry
Explain:

- coordinate system
- reference point
- polygon algorithm
- line intersection
- boundary behavior

### 5. Zone Tests
Report entry, exit, occupancy, duplicate suppression, and boundaries.

### 6. Tripwire Tests
Report crossing, reverse crossing, parallel motion, and duplicate suppression.

### 7. Track Lifecycle
Report LOST/REMOVED behavior.

### 8. Performance
Report detector latency/FPS, tracker latency, spatial latency, end-to-end latency/FPS, dropped frames, and active tracks.

### 9. Real Video Validation
Use `videoplayback.mp4` and report qualitative observations without inventing accuracy percentages.

### 10. Problems Encountered
Report geometry, coordinate, lifecycle, performance, and dependency problems.

### 11. Limitations
Discuss perspective distortion, camera calibration, bounding-box jitter, occlusion, boundary ambiguity, and small objects.

### 12. Future Improvements
Possible future work:
- interactive zone editor
- polygon drawing UI
- camera calibration
- perspective/homography
- trajectory smoothing
- event persistence

Do not implement these unless explicitly required.

### 13. M6 Integration

Explain:

```text
SpatialEvent[]
   ↓
M6 Event Engine
   ↓
Security Event
```

### 14. Next Milestone
State that M6 introduces event interpretation and alert generation.

Then STOP.

---

## 60. Future Architecture

```text
VIDEO
  ↓
M2 INGESTION
  ↓
FRAME
  ↓
M3 DETECTION
  ↓
DETECTION[]
  ↓
M4 TRACKING
  ↓
TRACK[]
  ↓
M5 SPATIAL INTELLIGENCE
  ↓
SPATIAL EVENT[]
  ↓
M6 EVENT ENGINE
  ↓
SECURITY EVENT
  ↓
ALERT / LOG
```

Later:

```text
M7 Behavioral Analytics
M8 ANPR
M9 Face Intelligence
M10 Night Movement
M11 Suspicious Activity
...
```

---

## 60A. Canonical Benchmark Policy

The same canonical traffic video should be reused across M3, M4, M5 and later benchmark milestones whenever the test is applicable.

Do not silently replace the benchmark clip because a different video gives better numbers.

Maintain the canonical asset metadata in shared project documentation:

```text
filename
duration
source FPS
resolution
codec/container
frame count
purpose
```

If the canonical file cannot be committed to the repository because of size/licensing constraints, document how the team obtains the exact same file and verify its checksum before benchmarking.

The benchmark path itself must remain machine-independent.

---


---

## 61. Engineering Principles

1. Spatial intelligence operates on tracks.
2. Camera geometry is isolated per camera.
3. Pixel coordinates are not physical-world coordinates.
4. Do not infer real-world distance or speed yet.
5. Bottom-center is the initial ground-contact reference point.
6. Boundary behavior must be deterministic.
7. Do not generate repeated events from persistent states.
8. LOST is not automatically EXIT.
9. Spatial events are facts, not security alerts.
10. No cross-camera identity.
11. Do not fabricate geometry accuracy.
12. Keep spatial history bounded.
13. Preserve source/camera/track traceability.
14. Measure before optimizing.
15. Do not implement M6 logic prematurely.

---

## 62. Final Instruction to Antigravity

Implement **Milestone 5 only**.

Start by inspecting and preserving M1–M4.

Build a clean, camera-specific spatial intelligence layer consuming:

```text
Track[]
```

and producing:

```text
SpatialEvent[]
```

Implement:

- zones
- polygons
- point-in-polygon
- zone entry
- zone exit
- occupancy
- tripwires
- line intersection
- crossing direction
- duplicate-event suppression
- camera isolation
- spatial configuration validation
- spatial visualization
- deterministic geometry tests

Use the canonical benchmark video through the configured test-video path.

Preferred repository-relative default:

```text
tests/assets/videoplayback.mp4
```

with an environment/configuration override:

```text
IBVAP_TEST_VIDEO
```

Do not hardcode any developer-specific absolute path.

Do not add:

- alerts
- intrusion classification
- suspicious activity
- loitering
- ANPR
- OCR
- face recognition
- behavioral analytics
- cross-camera identity
- command-center dashboard

Keep M1–M4 frozen.

Run clean benchmarks without visualization and separate visualization validation.

Measure M5 overhead and ensure spatial processing does not become a bottleneck.

When all acceptance criteria are satisfied, provide the final M5 report.

**STOP. Do not automatically implement Milestone 6.**
