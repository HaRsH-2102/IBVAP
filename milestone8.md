# IBVAP — Milestone 8 Specification

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Milestone:** M8 — Night-Time Movement & Low-Light Intelligence  
**Status:** 🟡 SPECIFICATION — NOT STARTED  
**Prerequisites:** M1–M7 completed and frozen

---

## 1. Milestone Purpose

M8 addresses one of the explicit SIH26187 requirements:

> **Night-time movement detection**

The system must detect meaningful human/vehicle movement under low-light and night-time conditions while preserving the existing architecture.

M8 is NOT simply a video-brightening module.

The objective is:

```text
Night/Low-Light Video
        ↓
Existing M3 Detection
        ↓
M4 Tracking
        ↓
M5 Spatial Intelligence
        ↓
M7 Behavioral Intelligence
        ↓
M8 Night-Time Intelligence
        ↓
M6 Event / Alert Pipeline
```

M8 determines whether the scene is operating under low-light conditions and provides dedicated night-time movement/context intelligence.

---

## 2. Core Objective

M8 must provide:

- automatic day/low-light/night classification
- configurable low-light thresholds
- low-light detection quality monitoring
- night-time movement detection
- suppression of obvious lighting-related false positives
- integration with existing tracks and spatial events
- configurable night-specific security rules
- explainable evidence for every night-time event

The first implementation must remain **software-defined and lightweight**.

Do not immediately introduce a large deep-learning enhancement model.

---

## 3. Critical Architecture Rule

M8 must NOT replace M3, M4, M5, M6, or M7.

```text
M2 Video Ingestion
        ↓
M3 Object Detection
        ↓
M4 Tracking
        ↓
M5 Spatial Intelligence
        ↓
M7 Behavioral Intelligence
        ↓
M8 Night-Time Intelligence
        ↓
M6 Policy / Alert Layer
```

M8 produces structured events/context.

M6 remains the only layer responsible for alert severity and operational alerts.

---

## 4. What M8 Must NOT Implement

Do NOT implement:

- facial recognition
- ANPR
- OCR
- cross-camera Re-ID
- weapon detection
- audio detection
- thermal-camera processing
- infrared hardware integration
- autonomous response
- command-center UI
- SMS/email/WhatsApp integration
- drone integration
- advanced threat classification
- large-scale low-light generative enhancement
- modification of M1–M7 core behavior
- another alert manager

---

## 5. Day/Low-Light/Night Detection

Compare lightweight approaches:

### A. Timestamp-Based

Use source timestamps or configured sunrise/sunset periods.

Pros: extremely cheap and deterministic.

Cons: does not necessarily reflect actual illumination.

### B. Frame Brightness Analysis

Estimate:

```text
mean luminance
median luminance
dark-pixel percentage
contrast
```

Pros: source-independent and cheap.

Cons: headlights and exposure changes can distort results.

### C. Hybrid

Preferred initial architecture:

```text
timestamp context
+
frame luminance
+
temporal consistency
```

The implementation must document the final method.

---

## 6. Low-Light State Machine

Use explicit states:

```text
DAY
 ↓
LOW_LIGHT
 ↓
NIGHT
```

and:

```text
NIGHT
 ↓
LOW_LIGHT
 ↓
DAY
```

Do not switch state based on a single frame.

Use temporal smoothing and hysteresis.

---

## 7. Low-Light Hysteresis

Brightness fluctuates because of:

- headlights
- streetlights
- clouds
- automatic exposure
- automatic gain
- passing vehicles

Use configurable:

```text
enter threshold
exit threshold
minimum state duration
smoothing window
```

Starting demonstration values:

```text
enter threshold = 45 luminance
exit threshold = 60 luminance
```

These are not operational thresholds.

---

## 8. Brightness Sampling

Do not perform unnecessary expensive full-resolution analysis.

Preferred starting approach:

```text
frame
 ↓
downsample
 ↓
grayscale
 ↓
luminance statistics
```

Sampling may occur periodically.

Benchmark the overhead.

---

## 9. Headlight Handling

Do not rely solely on mean brightness.

A night road with headlights can produce a high mean brightness.

Consider:

```text
median luminance
dark-pixel ratio
luminance percentiles
temporal consistency
```

Test explicit headlight scenarios.

---

## 10. Scene Context

M8 should expose:

```text
scene_state
brightness
dark_pixel_ratio
timestamp
```

Example:

```text
scene_state = NIGHT
brightness = ...
dark_pixel_ratio = ...
```

M6 can then use:

```text
RESTRICTED_ZONE_DWELL
+
scene_state = NIGHT
→ HIGH
```

M8 must not hardcode alert severity.

---

## 11. Night Movement Definition

Night movement is based on existing M4 tracks.

Example:

```text
scene = NIGHT
+
track exists
+
meaningful displacement
```

→ `NIGHT_MOVEMENT`

Brightness changes alone must NEVER generate movement events.

---

## 12. Movement Reference Point

Use the same M5/M7 reference:

```text
bottom-center of bounding box
```

Do not introduce another coordinate convention.

---

## 13. Movement Coordinate Space & Measurement

M8 movement calculations MUST use the **source-frame coordinate system** carried by M4/M5 `Track` bounding boxes.

M3's internal YOLO inference size (for example 1280×1280) must NOT be confused with the movement coordinate space.

Conceptually:

```text
Source frame: 1920×1080
       ↓
M3 internal preprocessing
       ↓
YOLO inference
       ↓
Detection/Track coordinates mapped to source-frame space
       ↓
M4 → M5 → M7 → M8
```

Therefore, the development default:

```text
movement_distance_threshold = 20 pixels
```

means **20 pixels in source-frame coordinates**.

Every benchmark must record:

```text
source resolution
inference resolution
movement coordinate resolution
movement threshold
```

Do not assume the same pixel threshold represents the same physical movement across cameras.

Use a temporal interval:

```text
position(t)
position(t - Δt)
```

Calculate displacement using timestamps.

Do not rely on a single-frame displacement.

Starting configuration:

```text
movement_distance_threshold = configurable
movement_duration_threshold = configurable
```

Pixel thresholds must be documented with the camera resolution.

---

## 14. Night Movement State Machine

Per track:

```text
NO_MOVEMENT
      ↓
MOVING
      ↓
EVENT_ACTIVE
      ↓
ENDED
```

Do not emit a new event every frame.

A continuous movement episode should be one logical occurrence.

---

## 15. NightMovementEvent Contract

Conceptually:

```text
NightMovementEvent
├── event_id
├── camera_id
├── track_id
├── object_class
├── timestamp
├── start_time
├── end_time
├── duration
├── displacement
├── scene_state
├── brightness_metrics
├── spatial_context
└── evidence
```

Example evidence:

```text
Track: cam01-42
Scene: NIGHT
Movement: 87 px
Duration: 3.2 sec
Zone: restricted_zone_01
```

Every event must be explainable.

---

## 16. Movement Deduplication

Do not emit:

```text
NIGHT_MOVEMENT
NIGHT_MOVEMENT
NIGHT_MOVEMENT
```

every frame.

Maintain:

```text
NOT_MOVING
    ↓
MOVING
    ↓
EVENT_ACTIVE
    ↓
ENDED
```

---

## 17. Lighting-Change Suppression

M8 must distinguish:

```text
scene illumination change
```

from:

```text
object movement
```

Test:

- headlights
- streetlight changes
- exposure adjustment
- automatic gain changes
- sudden flashes

These must not independently trigger movement.

---

## 18. Object-Class Awareness

Use existing M3/M4 classes where available:

```text
PERSON
CAR
MOTORCYCLE
BUS
TRUCK
```

Do not create another classifier.

M8 may apply different configurable policies later, but class detection remains M3/M4 responsibility.

---

## 19. Night-Time Spatial Context

M8 may combine night context with M5 context.

Example:

```text
NIGHT
+
PERSON
+
ZONE_ENTER
+
restricted zone
```

M8 can produce contextual information.

M6 determines whether it becomes HIGH/MEDIUM/LOW.

---

## 20. M7 Integration

Before implementation, inspect the actual frozen M7 `BehavioralEvent` contract and adapt M8 to it. **Do not modify M7 merely for M8 compatibility.**

M8 may enrich behavioral events with:

```text
scene_state = NIGHT
```

Example:

```text
LOITERING
+
NIGHT
+
zone_01
```

M7 remains responsible for loitering.

M8 must not duplicate M7 detectors.

---

## 21. M6 Correlation Boundary

M8 must NOT implement advanced cross-event correlation.

Do not require M6 to simultaneously correlate independent `BehavioralEvent` and `NightMovementEvent` objects in the first M8 implementation.

Preferred approach:

```text
M7 BehavioralEvent
        +
night context metadata
        ↓
single enriched event
        ↓
existing M6 Rule Engine
```

or:

```text
M8 NightMovementEvent
        ↓
existing M6 Rule Engine
```

For example:

```text
BehavioralEvent:
    behavior = LOITERING
    scene_state = NIGHT
    zone_id = zone_01
```

can be matched as one event by M6.

Advanced multi-event temporal correlation remains future work and must not be added by M8.

---

## 22. Recommended Integration

```text
                    ┌── M5 Spatial Events ──┐
                    │                       │
M4 Tracks ──────────┼── M7 Behaviors ───────┼──→ M8 Context
                    │                       │
                    └───────────────────────┘
                                ↓
                         Night Events
                                ↓
                               M6
```

M8 may consume:

- `Track[]`
- `SpatialEvent[]`
- `BehavioralEvent[]`
- `SceneState`

depending on implementation.

---

## 23. Configuration

All thresholds must support a global default and camera-specific overrides.

Conceptually:

```text
Global defaults
      ↓
Camera-specific override
```

Example:

```text
default:
    low_light_enter = 45
    low_light_exit = 60

camera_01:
    low_light_enter = 40
    low_light_exit = 55

camera_02:
    low_light_enter = 52
    low_light_exit = 68
```

If no camera-specific override exists, use the global value.

This is important because different cameras may have different exposure/gain characteristics, mounting environments, shadows, and optics.

Externalize:

```text
night_detection_enabled
low_light_enter_threshold
low_light_exit_threshold
scene_smoothing_window
minimum_night_state_duration

movement_distance_threshold
movement_duration_threshold
movement_smoothing_window

brightness_sample_interval
dark_pixel_ratio_threshold
```

Never hardcode operational thresholds.

---

## 24. Demonstration Defaults

Starting development values:

```text
low_light_enter_threshold = 45
low_light_exit_threshold = 60

scene_smoothing_window = 15 frames
minimum_night_state_duration = 2 seconds

movement_distance_threshold = 20 pixels
movement_duration_threshold = 1 second

brightness_sample_interval = 5 frames
```

These are development defaults only and must be validated against actual footage.

---

## 25. Resolution & Perspective

Pixel movement thresholds depend on camera resolution.

Document:

```text
source resolution
inference resolution
movement coordinate space
threshold
```

Do not assume 20 pixels represents the same physical movement on every camera.

Future improvements may use:

- normalized coordinates
- camera calibration
- homography
- ground-plane mapping

Do not implement these unless required by M8 acceptance.

---

## 26. Accuracy Claims

Do not claim:

```text
98% night detection accuracy
```

without labeled ground truth.

Report instead:

```text
expected scene state
actual scene state
false state transitions
transition latency

expected movement
actual movement event
false positives
missed events
```

---

## 27. Testing Strategy

Required tests:

### Scene tests

- brightness calculation
- dark-pixel ratio
- scene classification
- hysteresis
- state transitions

### Lighting tests

- headlights
- exposure changes
- brief flashes
- streetlights
- shadows

### Movement tests

- stationary object
- slow movement
- fast movement
- jitter
- occlusion
- LOST → ACTIVE

---

## 28. Synthetic Night Tests

### Test A — Stable Day

Expected:

```text
DAY
no night event
```

### Test B — Stable Dark Scene

Expected:

```text
NIGHT
```

### Test C — Borderline Brightness

Expected:

```text
LOW_LIGHT
```

### Test D — Headlights

Expected:

```text
NIGHT or LOW_LIGHT
```

not DAY solely because of headlights.

### Test E — Exposure Flicker

Expected:

```text
stable scene state
```

### Test F — Night Moving Person

Expected:

```text
NIGHT_MOVEMENT
```

### Test G — Night Stationary Person

Expected:

```text
no movement event
```

---

## 29. Jitter Tests

Test:

```text
1–2 px jitter
5 px jitter
10 px jitter
```

against configured thresholds.

Small tracking noise must not become night movement.

---

## 30. Track Lifecycle Tests

Test:

```text
ACTIVE
 ↓
LOST
 ↓
ACTIVE
```

and:

```text
ACTIVE
 ↓
REMOVED
```

State must recover correctly in the first case and be cleaned in the second.

No false event should be emitted simply because a track disappears.

---

## 31. Real-Video Validation & Dataset Provenance

Keep:

```text
videoplayback.mp4
```

as the canonical M3–M7 regression asset. Do NOT replace it.

Because it may not contain sufficient true night conditions, M8 must add separate low-light/night footage.

Do NOT allow the agent to arbitrarily download an unverified internet video.

Candidate public datasets to investigate include:

- **BDD100K** — useful for driving/night-scene research; verify the current dataset license and permitted use before downloading.
- **UA-DETRAC** — useful for traffic detection/tracking research; verify the current license and redistribution/use terms.
- **NightOwls** — useful for nighttime pedestrian detection research; verify the current license and dataset access terms.

The agent must verify the **current license/provenance** of any selected footage before incorporating it. If these candidates do not provide suitable footage under acceptable terms, use another clearly licensed source and document why it was selected.

Every M8 test asset must record:

```text
filename
source/provider
source URL or dataset reference
license
download/access date
resolution
FPS
duration
purpose
```

Recommended test categories:

1. daytime traffic
2. dusk/twilight
3. night traffic
4. dark road
5. headlights
6. low-light pedestrian movement
7. stationary night scene
8. exposure/gain fluctuations

---

## 32. Performance Requirements

Initial targets:

```text
Scene analysis < 1 ms/frame
Night movement analysis < 1 ms/active track/frame
Total M8 overhead < 2 ms/frame under normal load
```

Measure separately from M3 inference.

---

## 33. GPU Policy

M8 should NOT consume significant GPU resources for basic scene analysis.

Preferred:

```text
CPU:
brightness
scene state
trajectory movement

GPU:
M3 YOLO inference
```

Do not move simple image statistics to GPU unless profiling proves a real benefit.

The RTX 4060 should remain primarily available for M3 AI inference.

---

## 34. Memory Requirements

M8 state must be bounded.

Per camera:

```text
scene state
brightness history
transition state
```

Per track:

```text
movement state
bounded movement history
```

When a track becomes `REMOVED`, clean its M8 state.

---

## 35. Timestamp Policy

M8 must use one consistent timestamp convention internally.

Preferred production convention:

```text
timezone-aware UTC timestamps
```

Do not mix timezone-aware and timezone-naive datetimes.

If legacy upstream data requires adaptation, normalize it at the M8 boundary and document the conversion. Do not silently swallow timestamp errors.

All temporal calculations must use the same normalized representation.

---

## 45. Failure Isolation

If scene classification fails:

```text
M3/M4/M5/M7 continue
```

If one track's movement calculation fails:

```text
other tracks continue
```

Log:

```text
camera_id
track_id
timestamp
component
error
```

---

## 45. M6 Integration

M8 events must enter the existing M6 architecture.

Example:

```text
NIGHT_MOVEMENT
+
zone_01
+
PERSON
```

M6 rule:

```text
NIGHT_MOVEMENT
+
zone_01
+
PERSON
→ HIGH alert
```

M8 must never directly create alerts.

---

## 45. Multi-Camera Isolation

Scene state must be keyed by:

```text
camera_id
```

Track state by:

```text
camera_id + track_id
```

Camera A's illumination state must never affect Camera B.

---

## 45. Deterministic Event Ordering

Recommended:

```text
timestamp
→ camera_id
→ track_id
→ event_type
```

Do not depend on thread ordering.

---

## 45. Dependencies & Licensing

Every new dependency must document:

- exact package
- version
- license
- purpose
- runtime/development use
- performance impact

Prefer the existing OpenCV/NumPy infrastructure for the first implementation.

---

## 45. Privacy

M8 introduces no biometric processing.

It operates on:

```text
scene statistics
tracks
object classes
movement
spatial context
timestamps
```

No identity recognition should be introduced.

---

## 45. Acceptance Criteria

M8 is complete only when:

### Scene Intelligence

- [ ] day detection
- [ ] low-light detection
- [ ] night detection
- [ ] temporal smoothing
- [ ] hysteresis
- [ ] headlight robustness
- [ ] exposure-change robustness

### Movement Intelligence

- [ ] night movement detection
- [ ] per-track state
- [ ] movement threshold
- [ ] movement duration
- [ ] deduplication
- [ ] jitter resistance
- [ ] LOST handling
- [ ] REMOVED cleanup

### Integration

- [ ] M5 context supported
- [ ] M7 context supported
- [ ] M6 event ingestion supported
- [ ] no second alert system
- [ ] M1–M7 remain frozen

### Testing

- [ ] unit tests
- [ ] hysteresis tests
- [ ] headlight tests
- [ ] exposure tests
- [ ] jitter tests
- [ ] synthetic night tests
- [ ] night-video tests
- [ ] M6 regression tests
- [ ] performance benchmark

### Performance

- [ ] scene analysis measured
- [ ] movement analysis measured
- [ ] total M8 overhead measured
- [ ] memory growth measured

### Scope

- [ ] no ANPR
- [ ] no face recognition
- [ ] no Re-ID
- [ ] no thermal hardware
- [ ] no autonomous response
- [ ] no M9+ functionality

---

## 45. Completion Report Requirements

When M8 is complete, report:

1. architecture
2. modules/files changed
3. scene-state model
4. low-light detection algorithm
5. hysteresis strategy
6. brightness metrics
7. headlight handling
8. movement detector
9. movement state machine
10. jitter strategy
11. track lifecycle handling
12. M5 integration
13. M7 integration
14. M6 integration
15. configuration
16. synthetic test results
17. night-video results
18. false-positive results
19. performance metrics
20. memory metrics
21. dependency/license changes
22. limitations
23. future enhancement path
24. acceptance checklist
25. final M8 status

Do not claim accuracy without labeled ground truth.

---

## 45. Implementation Order

Build incrementally:

```text
Step 1  — SceneState contract
Step 2  — Brightness/luminance analyzer
Step 3  — Day/Low-Light/Night classifier
Step 4  — Temporal smoothing + hysteresis
Step 5  — Synthetic scene tests
Step 6  — Track movement feature extraction
Step 7  — Night movement state machine
Step 8  — Movement deduplication
Step 9  — M5/M7 context integration
Step 10 — M8 → M6 integration
Step 11 — Unit + edge-case testing
Step 12 — Night-video validation
Step 13 — Performance/memory benchmark
Step 14 — Completion report
```

Validate every stage independently.

Do not implement everything in one uncontrolled change.

---

## 45. Final Instruction to Antigravity

You are now starting **M8**.

M1–M7 are frozen.

Do not modify completed milestones unless a reproducible integration defect is discovered and explicitly documented.

Start with:

```text
Frame
+
Track[]
+
M5 SpatialEvent[]
+
M7 BehavioralEvent[]
```

and establish:

```text
SceneState
+
NightMovementEvent[]
```

Then integrate those events into the existing M6 policy/alert pipeline.

The first M8 implementation must be:

- deterministic
- explainable
- configurable
- lightweight
- timestamp-driven
- resistant to brightness fluctuations
- resistant to tracking jitter
- bounded in memory
- CPU-efficient
- compatible with future ML enhancement
- independent of biometric identity

Do not build a low-light deep-learning enhancement system unless profiling proves it necessary.

Do not consume GPU resources for trivial brightness calculations.

Do not create a second alert manager.

Do not modify M1–M7 casually.

Do not claim accuracy without labeled ground truth.

Do not proceed to M9.

After all M8 acceptance tests pass, produce the completion report and STOP.

**M8 begins here.**
