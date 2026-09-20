# IBVAP — Milestone 4
## Multi-Object Tracking

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Development agent:** Google Antigravity  
**Milestone:** 4 — Multi-Object Tracking / Temporal Identity Layer  
**Prerequisites:** Milestones 1, 2, and 3 completed and validated  
**Current M3 baseline:** YOLOv8n, RTX 4060, batch size 1, 1280×1280, confidence 0.25  
**Canonical traffic benchmark:** `videoplayback.mp4`

---

# 1. Purpose

Milestone 3 gave IBVAP frame-level object detections.

M4 adds **temporal identity**.

The system must determine whether detections appearing in consecutive frames represent the same physical object.

The pipeline becomes:

```text
Video
  ↓
M2 Video Ingestion
  ↓
Frame
  ↓
M3 Object Detector
  ↓
Detection[]
  ↓
M4 Multi-Object Tracker
  ↓
Track[]
```

M3 answers:

> What objects are visible in this frame?

M4 answers:

> Which detections belong to the same object over time?

Example:

```text
Frame 101 → Car, Person, Car
Frame 102 → Car, Person, Car
Frame 103 → Car, Person, Car
```

M4 should maintain identities such as:

```text
Track 17 → Car
Track 22 → Person
Track 31 → Car
```

---

# 2. Critical Scope Rule

M4 is ONLY about multi-object tracking.

Do NOT implement:

- virtual fences
- intrusion detection
- line crossing
- loitering
- suspicious activity
- risk scoring
- alerts
- ANPR
- OCR
- face detection/recognition
- person re-identification across cameras
- behavioral classification
- speed enforcement
- automatic incident generation
- production dashboard
- distributed tracking
- multi-camera identity fusion
- advanced GPU optimization unless a measured bottleneck requires it

A track is only:

> A sequence of detections believed to correspond to the same physical object over time.

---

# 3. First Action — Inspect M1, M2, and M3

Before implementation:

1. Inspect Milestone 1 domain contracts.
2. Inspect Milestone 2 video pipeline.
3. Inspect M3 `Detection`.
4. Inspect `BaseDetector`.
5. Inspect `YOLODetector`.
6. Inspect current configuration, logging, metrics, and tests.
7. Preserve existing architecture unless a genuine incompatibility exists.

Do not rewrite the detector or ingestion pipeline merely to add tracking.

The tracker consumes `Detection[]`.

---

# 4. Target Architecture

```text
Video Source
     ↓
M2 Frame Pipeline
     ↓
Frame
     ↓
M3 YOLO Detector
     ↓
Detection[]
     ↓
M4 Object Tracker
     ↓
Track[]
     ↓
Future spatial/event layers
```

The tracker must not know how the frame was captured and must not directly access the video source.

---

# 5. Tracker Abstraction

Create a replaceable tracker abstraction:

```text
BaseTracker
    │
    └── Concrete Tracker
```

Potential future implementations:

```text
BaseTracker
├── ByteTrackTracker
├── BoT-SORTTracker
├── DeepSORTTracker
└── FutureTracker
```

Only one implementation is required for M4.

Do not implement several trackers unless a controlled benchmark genuinely requires it.

---

# 6. Initial Tracker Selection

Use a tracker prioritizing:

- real-time performance
- reliability
- simplicity
- compatibility with YOLO detections
- persistent IDs
- low computational overhead

**ByteTrack is the preferred initial candidate.**

Do not assume it is permanently final. Preserve `BaseTracker` so alternatives can be evaluated later.

---

# 7. Why Tracking Is Required

Tracking enables:

- object dwell duration
- movement direction
- zone entry/exit
- unique-object counting
- trajectories
- future behavioral analysis

The future pipeline is:

```text
Detection
   ↓
Track
   ↓
Trajectory
   ↓
Spatial reasoning
   ↓
Event
```

M4 establishes only the Track layer.

---

# 8. Track Domain Model

Create or complete a `Track` domain model.

At minimum support:

- track ID
- camera/source ID
- object class
- current bounding box
- confidence
- current frame ID
- current timestamp
- lifecycle state
- age
- consecutive hits/updates
- time since last detection

Where useful support:

- centroid
- previous centroid
- trajectory history
- first-seen timestamp
- last-seen timestamp

Do not add event/risk fields.

---

# 9. Track ID Rules

Track IDs must be unique within the appropriate camera/session context.

At minimum:

```text
camera_id + track_id
```

must uniquely identify an active track.

Do not assume Track 17 on CAM01 is the same object as Track 17 on CAM02.

Do not make IDs globally persistent across application restarts in M4.

Prefer simple monotonic session-local IDs.

---

# 10. Track Lifecycle

Support a clear lifecycle, for example:

```text
NEW
 ↓
TENTATIVE
 ↓
CONFIRMED
 ↓
LOST
 ↓
REMOVED
```

The exact states may follow the selected tracker.

The system must distinguish newly observed, stable, temporarily missing, and terminated tracks.

---

# 11. Track Creation

When a detection cannot be associated with an existing track:

```text
Detection
   ↓
No suitable match
   ↓
New Track
   ↓
Track ID assigned
```

The track inherits source/camera, class, box, timestamp, and frame ID.

---

# 12. Track Association

Conceptually:

```text
Existing Tracks + New Detections
             ↓
        Association
             ↓
   ┌─────────┼─────────┐
Matched   New tracks   Lost tracks
```

Use the selected tracker's established association method.

Do not replace it with a simplistic nearest-centroid algorithm merely for convenience.

---

# 13. Detection-to-Track Traceability

Maintain the relationship:

```text
Track
 ├── Detection at Frame 101
 ├── Detection at Frame 102
 ├── Detection at Frame 103
 └── Detection at Frame 104
```

At minimum, the current track must remain traceable to its current detection/frame.

This is required for future trajectory analysis.

---

# 14. Track History

Maintain bounded history where practical.

Do NOT store every frame for the entire video.

Useful history fields:

- timestamp
- frame ID
- centroid
- bounding box
- confidence

Make maximum history configurable if implemented.

---

# 15. Centroid

For:

```text
x1, y1, x2, y2
```

calculate:

```text
cx = (x1 + x2) / 2
cy = (y1 + y2) / 2
```

Centroid is for geometry and future trajectory analysis.

Do NOT interpret pixel movement as physical-world distance or speed yet.

---

# 16. Trajectory

A trajectory is a sequence of positions:

```text
Track 17

(t1, x1, y1)
(t2, x2, y2)
(t3, x3, y3)
(t4, x4, y4)
```

This becomes the basis for future:

- direction
- line crossing
- zone transitions
- loitering
- path analysis

Do not implement those behaviors now.

---

# 17. Track Loss

Objects may disappear because of:

- occlusion
- detector misses
- motion blur
- lighting
- crowds
- frame drops

Do not immediately destroy a track after one missed detection.

Use the selected tracker’s standard lost-track behavior.

Conceptually:

```text
Detected
   ↓
Temporarily missing
   ↓
LOST
   ↓
Reappears → continue if association succeeds
```

Do not claim perfect recovery.

---

# 18. Re-Identification

Do NOT implement cross-camera re-identification.

Within one camera, use the selected tracker’s normal association.

If an object disappears and reappears, record whether the tracker preserves its ID.

Do not claim perfect identity persistence.

---

# 19. Class Consistency

A track should normally preserve its semantic class.

Example:

```text
Track 17 = CAR
```

Do not casually allow:

```text
CAR → PERSON → TRUCK
```

because of one noisy detection.

Understand and document the selected tracker's class-aware behavior.

---

# 20. Confidence

Track confidence may use the current associated detection confidence.

Do not invent a new track-confidence formula unless necessary.

Keep:

- detection confidence
- tracking/association state

conceptually separate.

---

# 21. Tracking Configuration

Expose only useful configurable parameters, where supported:

- tracker configuration
- matching threshold
- lost-track duration
- minimum hits before confirmation
- maximum history length

Do not expose dozens of obscure parameters without a tuning need.

---

# 22. Detector/Tracker Integration

Expected flow:

```text
frame = pipeline.get_next_frame()

detections = detector.detect(frame)

tracks = tracker.update(detections, frame)
```

The tracker must NOT call YOLO directly.

Correct:

```text
Detector
   ↓
Detection[]
   ↓
Tracker
   ↓
Track[]
```

---

# 23. Frame Rate and Detector Rate

Do not assume detector FPS equals camera FPS.

Example:

```text
Camera    25 FPS
Detector  20 FPS
Tracker   20 updates/sec
```

The tracker must handle the actual detection stream.

Do not introduce complex adaptive scheduling unless required.

---

# 24. Batch Size

**Batch size = 1 per camera.**

Do not introduce multi-camera batching.

Future multi-camera GPU batching is an optimization-stage concern.

---

# 25. GPU Usage

Tracking may be CPU-based depending on the implementation.

Do not force tracking onto GPU unless it measurably benefits the selected implementation.

The main M3 GPU workload remains YOLO inference.

Measure tracker overhead separately.

---

# 26. Performance Metrics

Measure:

### Detector
- inference latency
- inference FPS

### Tracker
- update latency
- tracker FPS
- active tracks

### End-to-end
- frame → detection → tracking latency
- end-to-end FPS
- dropped frames

### Track behavior
- tracks created
- tracks confirmed
- tracks lost
- tracks removed
- average track lifetime
- maximum simultaneous active tracks

---

# 27. Track Stability Metrics

Where practical measure/observe:

- ID switches
- track fragmentation
- track persistence
- detection-to-track association rate

FPS alone does not establish tracking quality.

---

# 28. Tracking Accuracy Evaluation

Do not claim numerical tracking accuracy without ground truth.

Possible formal metrics later:

- IDF1
- MOTA
- MOTP
- HOTA
- ID switches
- track fragmentation

For M4, qualitative evaluation and a small manually annotated sample are sufficient where practical.

Do not build a full benchmark framework unnecessarily.

---

# 29. Canonical Benchmark Videos

Use the M3 benchmark philosophy.

### Benchmark A
`videoplayback.mp4`

### Benchmark B
Secondary surveillance scenario if available.

### Benchmark C
Stress/edge scenario if available.

Keep benchmark files consistent across milestones.

---

# 30. Traffic-Specific Tracking Evaluation

Because `videoplayback.mp4` is traffic footage, explicitly evaluate:

- multiple cars
- vehicles moving in similar directions
- vehicles passing one another
- motorcycles between cars
- partial occlusion
- vehicles entering/exiting
- distant vehicles
- dense traffic

Observe:

- ID stability
- ID switches
- track fragmentation
- lost/recovered tracks

Do not implement traffic-rule enforcement.

---

# 31. Person Tracking Evaluation

Where people are visible, evaluate:

- multiple people
- partial occlusion
- people crossing paths
- people entering/exiting
- distant people

Only tracking. No face recognition or identity recognition.

---

# 32. Visualization

Create a technical validation mode showing:

- bounding boxes
- object class
- confidence
- track ID
- optional trajectory trail
- FPS
- active track count

Visualization is not the final command-center dashboard.

---

# 33. Visualization Must Not Pollute Benchmarks

Use two modes:

### Benchmark mode
No visualization.

### Validation mode
Visualization enabled.

Do not mix their performance numbers.

---

# 34. Preserve M3 Baseline

Use the M3 detector baseline for controlled comparisons:

```text
YOLOv8n
RTX 4060
batch = 1
1280×1280
confidence = 0.25
```

Do not change the detector merely to make tracking results look better.

If a detector change is tested, report it separately.

---

# 35. Track ID Semantics

Track IDs must be:

- stable during a track lifetime
- unique within camera/session
- not reused while an active track still has that ID

Monotonic IDs are preferred.

Do not make IDs globally persistent across restarts.

---

# 36. Camera Isolation

Tracking must be isolated per camera:

```text
CAM01 → Detector → Tracker-01 → Tracks
CAM02 → Detector → Tracker-02 → Tracks
```

Never associate detections across cameras in M4.

---

# 37. Error Handling

Handle:

- tracker initialization failure
- invalid detections
- malformed boxes
- unexpected detector output
- tracker update failure
- empty detection lists
- frame gaps
- source shutdown

An empty detection list is valid, not an error.

---

# 38. Empty Detection Handling

Test:

```text
detections = []
```

The tracker must:

- not crash
- update lost-track state
- retain tracks according to configured lifecycle rules
- eventually remove tracks according to the tracker policy

Do not delete every track immediately because one frame has no detections.

---

# 39. Invalid Detection Handling

Validate:

- bounding-box coordinates
- confidence range
- object class
- frame association

Reject or safely handle malformed detections.

Do not corrupt tracker state.

---

# 40. Resource Management

Do not retain unlimited history.

When the camera pipeline stops:

- stop tracker
- clear active state
- release resources
- close visualization
- terminate workers cleanly

Check for memory growth during long runs.

---

# 41. Dependencies

Use one primary tracking implementation.

If ByteTrack is available through an existing supported ecosystem, prefer that route.

Do not install multiple tracking frameworks, Re-ID models, or DeepSORT/BoT-SORT packages unless a controlled experiment proves a need.

---

# 42. Licensing

Record:

- tracker library
- exact version
- license
- source

Keep tracker, detector, and benchmark-video licensing records separate.

Do not make unsupported legal conclusions. Flag licensing implications for future review.

---

# 43. Testing Plan

## Test A — Tracker initialization
Verify the tracker starts with valid configuration.

## Test B — Single-object sequence
Verify the same object maintains one ID across consecutive frames.

## Test C — Multiple objects
Verify separate IDs for multiple people/vehicles.

## Test D — Real traffic video
Run M4 on `videoplayback.mp4`.

Verify:
- vehicles receive IDs
- IDs persist
- multiple vehicles track simultaneously
- no crashes
- latency remains bounded

## Test E — Occlusion
Observe persistence, loss, recovery, and ID switches.

## Test F — Object crossing
Evaluate ID stability when objects cross paths.

## Test G — Object entry/exit
Verify creation and eventual removal.

## Test H — Empty detections
Verify tracker stability.

## Test I — Start/stop
Verify no stale tracks or resource leaks.

## Test J — Sustained run
Monitor:
- memory
- active tracks
- tracker latency
- end-to-end FPS
- ID stability

---

# 44. Acceptance Criteria

M4 is complete only when:

### Architecture
- `BaseTracker` exists.
- Concrete tracker is isolated.
- Tracker consumes `Detection[]`.
- Tracker produces `Track[]`.
- Detector and tracker remain separate.
- Camera pipelines remain isolated.

### Tracking
- New tracks can be created.
- Existing tracks persist across frames.
- Track IDs are stable during normal continuous detection.
- Lost and removed tracks are handled.
- Multiple simultaneous objects are supported.
- Class and bounding box are maintained.
- Frame/timestamp/source are preserved.
- Track history is bounded.

### Performance
- Tracker latency is measured.
- Detector and tracker latency are separate.
- End-to-end performance is measured.
- Runtime dropped frames are measured.
- Memory behavior is stable.

### Quality
- Real traffic video is used.
- Multiple vehicles are tested.
- Occlusion is observed.
- Entry/exit is tested.
- ID switches and fragmentation are documented where observed.
- No fabricated metrics are reported.

### Scope
Do NOT add:
- intrusion
- virtual fences
- line crossing
- loitering
- suspicious activity
- alerts
- ANPR
- face recognition
- cross-camera identity

---

# 45. Definition of Done

M4 is complete when:

1. Tracker abstraction is implemented.
2. One concrete tracker is integrated.
3. `Detection[] → Track[]` works.
4. Track IDs are generated.
5. IDs remain stable during normal continuous detection.
6. Multiple objects can be tracked simultaneously.
7. Person tracking works where people are present.
8. Vehicle tracking works.
9. Bounding boxes update correctly.
10. Source/camera identity is preserved.
11. Frame/timestamp information is preserved.
12. Track lifecycle is implemented.
13. Lost tracks are handled.
14. Removed tracks are handled.
15. Track history is bounded.
16. Centroids are available.
17. Basic trajectory history is available where implemented.
18. Empty detections are handled.
19. Invalid detections are handled.
20. Batch size remains 1 per camera.
21. M3 detector baseline is preserved.
22. `videoplayback.mp4` is used.
23. Tracking performance is measured.
24. ID switches/fragmentation are observed and documented.
25. No fabricated accuracy metrics are reported.
26. Tracker license/version is recorded.
27. No unnecessary second tracking framework is introduced.
28. Tests pass.
29. Antigravity stops after M4.

---

# 46. Required Final Report

After implementation, STOP and provide:

## 1. Summary
What was implemented?

## 2. Tracker
Report:
- tracker name
- exact implementation/package
- version
- license
- configuration

## 3. Architecture
Explain:

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
```

## 4. Track Contract
Explain all fields and coordinate conventions.

## 5. Track Lifecycle
Explain the actual lifecycle states used.

## 6. Association
Explain conceptually how detections are associated with tracks.

## 7. Performance
Report:
- source FPS
- detector FPS
- detector latency
- tracker latency
- end-to-end FPS
- end-to-end latency
- dropped frames
- average active tracks
- maximum active tracks
- memory usage where available

## 8. Tracking Quality
Report:
- track stability
- ID switches
- fragmentation
- occlusion behavior
- entry/exit behavior

If formal metrics were not calculated, explicitly say so.

## 9. Benchmark Videos
Identify:
- Benchmark A: `videoplayback.mp4`
- other benchmark clips
- relevant metadata

## 10. Problems Encountered
Report tracker, compatibility, ID-switch, performance, and dependency issues.

## 11. Limitations
Be honest about occlusion, crowds, small objects, detector misses, ID switches, and fragmentation.

## 12. Future Optimization
Discuss possible future improvements without implementing them:
- better tracker
- Re-ID
- appearance features
- GPU tracking
- detector/tracker scheduling
- multi-camera optimization

## 13. M5 Integration
Explain how `Track[]` will feed:

```text
Track[]
   ↓
Spatial Intelligence
   ↓
Zones / Virtual Fences / Line Crossing
```

## 14. Next Milestone
State that M5 introduces spatial intelligence primitives.

Then STOP.

---

# 47. Future Architecture

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
M6 EVENT ENGINE
  ↓
M7 BEHAVIOR
  ↓
M8 ANPR
  ↓
...
```

Later intelligence should operate on tracks whenever temporal identity is required.

---

# 48. Why M4 Must Stay Focused

M4 answers one question:

> **Can IBVAP maintain stable temporal identities for detected people and vehicles within an individual camera stream?**

If yes, M4 succeeds.

Do not hide tracking problems by adding spatial rules, alerts, behavior classifiers, or suspicious-activity logic.

Those belong to later milestones.

---

# 49. Engineering Principles

1. Detection and tracking remain separate.
2. Track IDs are temporal identities, not real-world identities.
3. Never claim perfect identity persistence.
4. One camera has an isolated tracker context.
5. Batch size remains 1 per camera.
6. Preserve source/frame/timestamp traceability.
7. Measure tracker overhead.
8. Keep history bounded.
9. Never fabricate tracking metrics.
10. Test on real traffic/surveillance footage.
11. Record ID switches rather than hiding them.
12. Prefer measured improvements over arbitrary tuning.
13. Do not introduce Re-ID unless actual tracking failures justify it.
14. Do not implement spatial/event intelligence prematurely.
15. Do not automatically continue to M5.

---

# 50. Final Instruction to Antigravity

Implement **Milestone 4 only**.

Start by inspecting and preserving the completed M1, M2, and M3 architecture.

Add a clean tracker abstraction and one concrete real-time multi-object tracker, with **ByteTrack as the initial candidate**.

The tracker must consume standardized M3 `Detection[]` objects and produce standardized M4 `Track[]` objects.

Use:

- existing M2 video pipeline
- existing M3 YOLO detector
- RTX 4060 M3 baseline
- batch size 1 per camera
- `videoplayback.mp4` as primary benchmark
- M3 detector configuration: YOLOv8n, 1280×1280, confidence 0.25, CUDA

Do not rewrite M2 or M3 unnecessarily.

Do not add tracking directly inside the detector.

Do not add:
- ANPR
- face recognition
- intrusion detection
- virtual fences
- line crossing
- loitering
- suspicious activity
- alerts
- risk scoring
- cross-camera identity
- production dashboard

Measure:
- detector performance
- tracker latency
- end-to-end performance
- active tracks
- track creation/removal
- ID stability
- ID switches
- track fragmentation
- memory behavior

Run:
1. clean benchmark mode without visualization
2. separate visualization validation mode

Do not mix visualization performance with benchmark performance.

Use real traffic/surveillance footage.

Do not fabricate tracking accuracy.

When M4 acceptance criteria are satisfied, provide the complete final report specified above and **STOP**.

Do not automatically implement Milestone 5.
