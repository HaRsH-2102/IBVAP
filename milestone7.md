# IBVAP — Milestone 7 Specification

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Milestone:** M7 — Suspicious Activity & Behavioral Intelligence  
**Status:** 🟡 SPECIFICATION — NOT STARTED  
**Prerequisites:** M1–M6 completed and frozen

---

## 1. Milestone Purpose

M1–M6 established:

```text
M2 — Video Ingestion
        ↓
M3 — Object Detection
        ↓
M4 — Multi-Object Tracking
        ↓
M5 — Spatial Intelligence
        ↓
M6 — Event Interpretation + Alerts
```

M7 introduces **temporal behavioral intelligence**.

The system moves from:

> Where is the object?

and:

> Did it cross a boundary?

toward:

> **What measurable movement pattern is this object exhibiting over time?**

The first M7 implementation must be **deterministic, explainable, configurable, and rule-based**. It must not begin with an opaque behavioral neural network.

---

## 2. Core Objective

Build a modular behavioral-analysis engine capable of detecting configurable patterns such as:

- loitering
- prolonged stationary presence
- restricted-zone dwell
- repeated zone entry/exit
- repeated boundary approaches
- meaningful direction reversals
- rapid backtracking

M7 produces structured `BehavioralEvent[]` that are consumed by M6.

```text
M4 Track[]
      │
      ├──────────────┐
      ▼              ▼
M5 spatial       M7 trajectory
context          analysis
      │              │
      └──────┬───────┘
             ▼
      BehavioralEvent[]
             │
             ▼
        M6 Rule Engine
             │
             ▼
       SecurityEvent
             │
             ▼
           Alert
```

---

## 3. Critical Boundary

M7 must NOT create a second alert system.

```text
M7:
"What behavior occurred?"

M6:
"What does that behavior mean operationally?"
```

Therefore:

```text
BehavioralEvent
      ↓
M6 Rule Engine
      ↓
SecurityEvent
      ↓
Alert Manager
      ↓
SQLite
```

M6 remains the single policy and alert layer.

---

## 4. What M7 Must NOT Implement

Do NOT implement:

- ANPR
- OCR
- facial recognition
- face embeddings
- cross-camera Re-ID
- weapon detection
- night-time detection
- audio analysis
- LLM reasoning
- autonomous threat classification
- autonomous response
- command-center UI
- SMS/email/WhatsApp integrations
- advanced deep-learning behavior models
- changes to M1–M6
- a second alert manager

---

## 5. Why Rule-Based First?

"Suspicious" is contextual.

For example:

```text
Person stopped for 30 seconds
```

does not automatically mean:

```text
Suspicious
```

M7 should instead report an observable behavior:

```text
LOITERING
```

M6 can then apply policy:

```text
LOITERING
+
restricted zone
→ HIGH alert
```

This provides:

- explainability
- deterministic tests
- easy debugging
- configurable policies
- low computational cost
- a clean path toward future ML

---

## 6. Initial Behavioral Event Vocabulary

Implement the following deterministic behaviors:

```text
LOITERING
STATIONARY_PROLONGED
RESTRICTED_ZONE_DWELL
REPEATED_ZONE_ENTRY
REPEATED_BOUNDARY_APPROACH
DIRECTION_REVERSAL
RAPID_BACKTRACK
```

Do not implement speculative behaviors without measurable definitions.

---

## 7. BehavioralEvent Contract

Conceptually:

```text
BehavioralEvent
├── event_id
├── behavior_type
├── camera_id
├── track_id
├── timestamp
├── start_time
├── end_time
├── duration
├── spatial_context
├── evidence
├── correlation_id
└── metadata
```

`end_time` may be null while a behavior is active.

Do not fabricate ML probabilities.

If a confidence field is used, it must represent a clearly defined evidence/confidence calculation.

---

## 8. Evidence-First Design

Every behavioral event must explain why it triggered.

Example:

```text
Behavior:
LOITERING

Evidence:
Track: cam01-17
Zone: zone_01
Duration: 48.2 sec
Movement radius: 18.7 px
Configured duration threshold: 45 sec
Configured movement threshold: 50 px
```

If a behavior cannot provide measurable evidence, it should not be implemented yet.

---

## 9. Trajectory Input

M7 primarily consumes the canonical M4 `Track`:

```text
Track
├── track_id
├── camera_id
├── object_class
├── bounding_box
├── trajectory[]
└── state
```

Do not create another tracker.

Use the existing M4 trajectory.

---

## 10. Reference Point

Use the M5 reference convention:

```text
bottom-center of bounding box
```

This keeps M5 and M7 spatial calculations consistent.

---

## 11. History

Maintain bounded behavioral history per:

```text
camera_id + track_id
```

Do not create unlimited history.

Starting maximum:

```text
300 trajectory points
```

consistent with the existing M4 bounded trajectory.

---

## 12. Timestamp-Based Timing

Behavior durations must use timestamps, not assumed FPS.

Correct:

```text
t2 - t1 = elapsed time
```

Incorrect:

```text
30 frames = 1 second
```

This is essential because M2 may drop stale frames under overload.

---

## 13. Loitering

Initial deterministic definition:

An object is potentially loitering when:

1. it remains within the configured monitored region,
2. for at least a configured duration,
3. its movement remains below a configured radius/threshold.

Starting demonstration values:

```text
duration = 45 seconds
movement radius = 50 pixels
```

These are configurable demonstration values, not operational border thresholds.

---

## 14. Loitering State Machine

```text
NOT_LOITERING
      ↓
OBSERVING
      ↓ duration + low movement
LOITERING
      ↓ movement/reset threshold
NOT_LOITERING
```

Do not emit LOITERING every frame.

One continuous loitering episode should produce one logical occurrence.

---

## 15. Loitering Reset

Reset when the object:

- leaves the monitored region
- exceeds movement threshold for the reset duration
- is removed
- the rule is disabled

Starting reset duration:

```text
3 seconds
```

Make it configurable.

Avoid single-frame resets.

---

## 16. Prolonged Stationary Detection

Detect an object that remains effectively stationary for a configured duration.

Starting values:

```text
duration = 30 seconds
movement radius = 15 pixels
```

Evidence must include:

```text
duration
movement radius
track_id
camera_id
```

Stationary does not automatically mean suspicious.

---

## 17. Restricted-Zone Dwell

Using M5 spatial context:

```text
ZONE_ENTER
      ↓
object remains inside
      ↓
configured duration
      ↓
RESTRICTED_ZONE_DWELL
```

Starting demonstration duration:

```text
30 seconds
```

M5 reports entry/exit; M7 reports prolonged temporal occupancy.

---

## 18. Repeated Zone Entry

Detect a repeated pattern:

```text
ENTER
EXIT
ENTER
EXIT
ENTER
```

Starting configuration:

```text
minimum entries = 3
window = 60 seconds
```

This is a measurable pattern, not proof of intent.

---

## 19. Repeated Boundary Approach

Detect repeated approaches toward a configured restricted boundary without crossing it:

```text
approach
retreat
approach
retreat
approach
```

Starting configuration:

```text
minimum approaches = 3
window = 60 seconds
```

Use measurable distance to M5 geometry.

Do not call this "attempted intrusion" automatically.

---

## 20. Direction Reversal

Detect meaningful changes in movement direction.

Example:

```text
→ → → → ← ← ←
```

A reversal must use meaningful displacement and temporal smoothing.

Do not trigger on tiny frame-to-frame jitter.

Configurable parameters should include:

- minimum displacement
- minimum directional change
- smoothing window
- reset threshold

---

## 21. Rapid Backtrack

Detect an object that:

1. moves a meaningful distance,
2. reverses direction,
3. returns toward its recent path within a short configurable period.

Starting example:

```text
maximum reversal window = 10 seconds
```

Do not label this behavior as malicious inside M7.

---

## 22. Per-Track Behavioral State

State is isolated by:

```text
camera_id + track_id
```

Example:

```text
CAM01 / Track17
├── loitering
├── stationary
├── dwell
├── entry history
└── direction history
```

No track may inherit another track's state.

---

## 23. Track Lifecycle

### ACTIVE

Evaluate normally.

### LOST

Preserve short-term state to tolerate temporary tracking gaps.

### REMOVED

Clean all behavioral state.

Do not generate false suspicious events merely because a track was removed.

---

## 24. Track Reappearance

If the same M4 track ID returns:

```text
LOST → ACTIVE
```

M7 may continue the existing history.

If a new track ID appears:

```text
old ID ≠ new ID
```

M7 must not assume they are the same physical object.

Cross-camera identity is deferred.

---

## 25. Behavioral Event Deduplication

Do not emit:

```text
LOITERING
LOITERING
LOITERING
```

every frame.

Behavior must have a lifecycle:

```text
NOT_ACTIVE
     ↓
TRIGGERED
     ↓
ACTIVE
     ↓
ENDED
```

A continuous behavior should produce one logical occurrence.

---

## 26. Behavioral Event Lifecycle

Each event should preserve:

```text
start_time
end_time
duration
```

For active events:

```text
end_time = null
```

When the behavior ends, update the same occurrence rather than creating a new event every frame.

---

## 27. Event Frequency Rules

Define emission frequency per behavior:

```text
Loitering:
one occurrence per continuous episode

Repeated entry:
one event per qualifying sequence

Direction reversal:
one event per meaningful reversal
```

Prevent event storms.

---

## 28. Spatial Context

M7 may associate behavior with:

```text
zone_id
line_id
restricted_area
```

Example:

```text
LOITERING
camera = CAM01
track = 17
zone = zone_01
duration = 48 sec
```

This lets M6 distinguish:

```text
LOITERING in normal area
```

from:

```text
LOITERING in restricted area
```

without embedding security policy in M7.

---

## 29. M7 → M6 Integration

M7 emits:

```text
BehavioralEvent[]
```

M6 must consume these through an extensible event-ingestion boundary.

Conceptually:

```text
SpatialEvent[] ─────┐
                    ├──→ M6
BehavioralEvent[] ──┘
```

M6 remains the only alert/policy engine.

---

## 30. Example M6 Policies

Example:

```text
RESTRICTED_ZONE_DWELL
duration >= 30 sec
zone = zone_01
→ HIGH alert
```

Another:

```text
REPEATED_BOUNDARY_APPROACH
→ MEDIUM security event
```

M7 reports behavior.

M6 determines operational significance.

---

## 31. Configuration

Externalize all thresholds:

```text
loitering_duration
loitering_radius
loitering_reset_duration

stationary_duration
stationary_radius

zone_entry_count
zone_entry_window

boundary_approach_count
boundary_approach_window

direction_change_threshold
backtrack_window
```

Do not scatter behavioral constants through code.

---

## 32. Demonstration Configuration

Start with:

```text
loitering:
    duration = 45 sec
    radius = 50 px
    reset_duration = 3 sec

stationary:
    duration = 30 sec
    radius = 15 px

restricted_zone_dwell:
    duration = 30 sec

repeated_zone_entry:
    count = 3
    window = 60 sec

repeated_boundary_approach:
    count = 3
    window = 60 sec

rapid_backtrack:
    window = 10 sec
```

These are demonstration defaults only.

---

## 33. Resolution & Perspective

Time thresholds are resolution-independent.

Pixel thresholds are not.

Document:

```text
camera resolution
reference resolution
pixel thresholds
```

Do not assume 50 pixels represents the same physical distance on every camera.

Future work may use:

- normalized coordinates
- camera calibration
- homography
- ground-plane mapping

Do not implement those in M7 unless required.

---

## 34. Smoothing & Jitter

Behavior analysis must resist tracker noise.

Use trajectory history and appropriate temporal smoothing.

Do not trigger behaviors from isolated frame-to-frame changes.

Document:

- smoothing method
- smoothing window
- thresholds
- reset behavior

---

## 35. Missing Frames

Use timestamps when frames are dropped.

Example:

```text
Frame A = 10.00 s
Frame B = 10.20 s
```

means 200 ms elapsed.

Never assume a fixed frame count represents fixed elapsed time.

---

## 36. Performance Target

M7 operates on tracks and geometry, not raw video.

Initial target:

```text
Average behavioral processing < 2 ms per active track
Maximum normal processing < 10 ms per active track
```

Measure separately from M3 inference.

Do not claim performance without a benchmark.

---

## 37. Memory Target

Behavioral history must be bounded.

Measure:

```text
active tracks
history points per track
behavior state objects
memory growth
state cleanup count
```

There must be no unbounded state after tracks become REMOVED.

---

## 38. Failure Isolation

If one behavior fails:

```text
Loitering → exception
Stationary → still runs
Reversal → still runs
```

Malformed configuration must not crash the pipeline.

One bad track must not stop other tracks.

Log:

```text
camera_id
track_id
behavior_type
timestamp
error
```

---

## 39. Deterministic Ordering

Sort behavioral events deterministically:

```text
timestamp
→ track_id
→ behavior_type
```

Never depend on dictionary or thread ordering.

---

## 40. Testing Strategy

M7 testing must be primarily deterministic.

### Unit tests

Each behavior with controlled trajectories.

### State-machine tests

```text
OBSERVING
→ TRIGGERED
→ ACTIVE
→ ENDED
```

### Integration

```text
M4 Track
 ↓
M7
 ↓
BehavioralEvent
 ↓
M6
 ↓
SecurityEvent
 ↓
Alert
```

### Real video

Use the canonical:

```text
videoplayback.mp4
```

---

## 41. Synthetic Trajectory Tests

Required fixtures:

### Loitering

Small movement for 45+ seconds:

```text
Expected → LOITERING
```

### Normal movement

Continuous movement:

```text
Expected → no LOITERING
```

### Repeated entry

```text
ENTER
EXIT
ENTER
EXIT
ENTER
```

Expected:

```text
REPEATED_ZONE_ENTRY
```

### Direction reversal

```text
→ → → → ← ← ←
```

Expected:

```text
DIRECTION_REVERSAL
```

### Jitter

Tiny random movement:

```text
Expected → no behavioral event
```

### Track removal

```text
ACTIVE
→ LOST
→ REMOVED
```

Expected:

```text
state cleaned
no false behavioral event
```

---

## 42. False-Positive Testing

Explicitly test:

- stationary vehicle at traffic light
- normal pedestrian pause
- tracking jitter
- brief direction change
- single zone re-entry
- short boundary approach
- temporary occlusion
- LOST → ACTIVE recovery

Do not automatically label these as suspicious.

---

## 43. Real-Video Validation

Use:

```text
videoplayback.mp4
```

without changing M3–M6 configurations.

Run:

```text
M2
 ↓
M3
 ↓
M4
 ↓
M5
 ↓
M6
 ↘
  M7
```

The real traffic video validates:

- pipeline integration
- trajectory stability
- behavior-event formatting
- performance
- robustness

It does **not** prove that thresholds are operationally correct for border environments.

---

## 44. Benchmark Outputs

Report:

```text
source_fps
received_fps
processed_fps
max_active_tracks

behavior_events_generated
events_by_behavior_type

avg_behavior_latency_ms
max_behavior_latency_ms

avg_active_tracks
max_active_tracks

history_memory_usage
state_cleanup_count
```

Do not report an accuracy percentage unless ground-truth labels exist.

---

## 45. Behavioral Accuracy

Do not claim:

```text
95% suspicious activity accuracy
```

from an unlabeled traffic video.

For deterministic rules report:

- expected events
- actual events
- false positives
- missed triggers
- trigger latency

Meaningful accuracy requires labeled ground truth.

---

## 46. M6 Regression Protection

Before M7 completion verify:

- M6 receives events correctly
- existing M6 spatial-event rules still work
- alerts persist
- alert lifecycle works
- SQLite recovery works
- M6 latency is not significantly degraded
- M1–M6 behavior remains unchanged

---

## 47. Performance Isolation

Benchmark separately:

```text
M3 — AI inference
M4 — tracking
M5 — spatial geometry
M7 — behavioral analysis
```

Do not attribute M3/M4 latency to M7.

---

## 48. Dependencies & Licensing

For every new dependency record:

- package
- exact version
- license
- purpose
- runtime/development use

Avoid heavy ML dependencies for deterministic trajectory rules.

---

## 49. No ML Model in First Pass

M7 must NOT train or deploy a behavioral neural network.

Reasons:

- no reliable project-specific behavioral dataset yet
- suspicious behavior is contextual
- deterministic rules are easier to validate
- explainability is important
- structured M7 features can support future ML

Future architecture:

```text
Trajectory Features
       ↓
ML Behavior Model
       ↓
Behavior Probability
       ↓
M6 Policy Engine
```

This is explicitly deferred.

---

## 50. Future ML Extension

Prepare structured features such as:

```text
speed
direction
acceleration
turning angle
dwell time
distance to boundary
zone occupancy
entry count
exit count
trajectory curvature
stop/start frequency
```

Do not implement the ML model now.

---

## 51. Privacy & Data Minimization

M7 introduces no biometric identity.

Use:

```text
camera_id
track_id
trajectory
behavior features
spatial context
timestamps
```

Avoid unnecessary raw-video storage.

---

## 52. Acceptance Criteria

M7 is complete only when:

### Architecture

- [ ] M1–M6 remain frozen
- [ ] M7 consumes Track/trajectory + M5 context
- [ ] M7 produces `BehavioralEvent[]`
- [ ] M7 does not create a second alert system
- [ ] M6 remains the policy/alert layer

### Behavioral Detection

- [ ] loitering
- [ ] prolonged stationary behavior
- [ ] restricted-zone dwell
- [ ] repeated zone entry
- [ ] repeated boundary approach
- [ ] direction reversal
- [ ] rapid backtrack
- [ ] configurable thresholds
- [ ] deterministic state machines
- [ ] behavioral deduplication

### Robustness

- [ ] timestamp-based duration
- [ ] jitter resistance
- [ ] missing-frame handling
- [ ] LOST handling
- [ ] REMOVED cleanup
- [ ] bounded memory
- [ ] no stale state accumulation

### Testing

- [ ] synthetic trajectory tests
- [ ] state-machine tests
- [ ] jitter tests
- [ ] false-positive tests
- [ ] integration tests
- [ ] M6 regression tests
- [ ] canonical real-video test
- [ ] performance benchmark

### Performance

- [ ] average behavioral latency measured
- [ ] maximum behavioral latency measured
- [ ] active-track count measured
- [ ] memory growth measured
- [ ] target comparison reported

### Scope

- [ ] no ANPR
- [ ] no OCR
- [ ] no face recognition
- [ ] no cross-camera Re-ID
- [ ] no night detection
- [ ] no deep-learning behavior model
- [ ] no command-center UI
- [ ] no autonomous response
- [ ] no M8+ functionality

---

## 53. Completion Report Requirements

When M7 is complete, Antigravity must report:

1. architecture
2. files/modules changed
3. BehavioralEvent contract
4. behavior definitions
5. threshold configuration
6. state-machine design
7. trajectory-processing strategy
8. smoothing/jitter strategy
9. missing-frame handling
10. track lifecycle handling
11. memory/state cleanup
12. synthetic-test results
13. false-positive results
14. integration-test results
15. M6 regression results
16. real-video results
17. performance metrics
18. memory metrics
19. behavior-event counts
20. known limitations
21. dependencies/licenses
22. future ML extension
23. acceptance checklist
24. final M7 status

Do not claim behavioral accuracy without labeled ground truth.

---

## 54. Implementation Order

Build incrementally:

```text
Step 1  — BehavioralEvent contract
Step 2  — Trajectory feature extraction
Step 3  — Per-track behavioral state
Step 4  — Loitering
Step 5  — Stationary detection
Step 6  — Restricted-zone dwell
Step 7  — Repeated zone entry
Step 8  — Boundary approach
Step 9  — Direction reversal
Step 10 — Rapid backtrack
Step 11 — Deduplication/lifecycle
Step 12 — M7 → M6 integration
Step 13 — Synthetic testing
Step 14 — Real-video validation
Step 15 — Performance/memory benchmark
Step 16 — Completion report
```

Validate each behavior independently.

Do not implement everything in one uncontrolled change.

---

## 55. Final Instruction to Antigravity

You are now starting **M7**.

M1–M6 are frozen.

Do not modify completed milestones unless a reproducible integration defect is discovered and explicitly documented.

Start from:

```text
Track[]
+
M5 spatial context
+
timestamps
```

and produce:

```text
BehavioralEvent[]
```

Then send those events into the existing M6 event/policy pipeline.

The first M7 implementation must be:

- deterministic
- explainable
- configurable
- timestamp-driven
- lightweight
- testable
- bounded in memory
- resistant to tracking jitter
- independent of raw video inference
- compatible with future ML

Prefer observable behavior names:

```text
LOITERING
REPEATED_ZONE_ENTRY
RESTRICTED_ZONE_DWELL
DIRECTION_REVERSAL
```

M6 determines security significance.

Do not build an ML behavior model yet.

Do not build a second alert system.

Do not implement ANPR, face recognition, night detection, Re-ID, or command-center UI.

Do not skip synthetic trajectory testing.

Do not claim accuracy without ground-truth labels.

Do not proceed to M8.

After completing all M7 acceptance tests, produce the completion report and STOP.

**M7 begins here.**
