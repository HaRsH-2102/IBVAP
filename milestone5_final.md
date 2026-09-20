# IBVAP — Milestone 5 Final Report & Freeze Record

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Milestone:** M5 — Spatial Intelligence  
**Status:** 🟢 PASS — FROZEN  
**Prerequisites:** M1, M2, M3, M4 completed and validated  
**Primary benchmark:** `videoplayback.mp4`  
**Detector:** YOLOv8n + NVIDIA RTX 4060 CUDA  
**Inference size:** 1280×1280  
**Confidence threshold:** 0.25  
**Tracker:** ByteTrack  
**Spatial reference point:** Bottom-center of bounding box  
**Zone/tripwire hysteresis:** 3.0 px at 1280×1280

---

## 1. Milestone Purpose

M5 introduces the **Spatial Intelligence Layer**.

M1 established the domain/application foundation, M2 video ingestion, M3 AI object detection, and M4 persistent temporal identities.

M5 adds the ability to understand **where tracked objects are relative to configured geometric regions and boundaries**.

```text
Video
  ↓
M2 — Ingestion
  ↓
Frame
  ↓
M3 — Object Detection
  ↓
Detection[]
  ↓
M4 — Multi-Object Tracking
  ↓
Track[]
  ↓
M5 — Spatial Intelligence
  ↓
SpatialEvent[]
  ↓
M6 — Event Interpretation
```

M5 produces geometric facts. It does not yet determine whether those facts constitute security incidents.

---

## 2. M5 Responsibilities

Implemented:

- camera-specific spatial configuration
- polygon zones
- virtual fences/tripwires
- point-in-polygon evaluation
- bottom-center reference points
- zone occupancy state
- zone entry
- zone exit
- line crossing
- crossing direction
- boundary hysteresis
- duplicate-event suppression
- spatial event generation
- spatial state management
- camera isolation
- deterministic event ordering
- spatial visualization
- geometry validation

Not implemented:

- alerts
- alarm escalation
- suspicious activity
- loitering
- behavioral classification
- risk scoring
- ANPR/OCR
- face recognition
- night movement detection
- cross-camera identity
- command-center integration
- notifications
- production dashboard
- GPS/world-coordinate mapping
- real-world distance/speed estimation

---

## 3. Frozen Architecture

```text
                    IBVAP
                      │
                      ▼
              ┌───────────────┐
              │ M2 Ingestion  │
              └───────┬───────┘
                      │ Frame
                      ▼
              ┌───────────────┐
              │ M3 Detection  │
              │ YOLO + CUDA   │
              └───────┬───────┘
                      │ Detection[]
                      ▼
              ┌───────────────┐
              │ M4 Tracking   │
              │   ByteTrack   │
              └───────┬───────┘
                      │ Track[]
                      ▼
              ┌───────────────┐
              │ M5 Spatial    │
              │ Intelligence  │
              └───────┬───────┘
                      │ SpatialEvent[]
                      ▼
              ┌───────────────┐
              │ M6 Event      │
              │ Interpretation│
              └───────────────┘
```

M5 consumes canonical M4 `Track[]` and does not perform detection or tracking.

---

## 4. Coordinate System

Camera-image coordinates use:

```text
(0,0)
  ┌────────────────────────────→ X
  │
  │
  │
  ↓
  Y
```

- origin = top-left
- X increases right
- Y increases downward
- coordinates are pixels
- geometry is camera-specific

---

## 5. Reference Point

The spatial reference point is the **bottom-center of the tracked bounding box**:

```text
x = (left + right) / 2
y = bottom
```

This approximates the ground-contact location better than the bounding-box center for many surveillance scenarios.

---

## 6. Camera-Specific Configuration

Each camera owns independent zones, tripwires, and spatial state.

```text
CAM01
 ├── zone_01
 ├── zone_02
 ├── line_01
 └── line_02

CAM02
 ├── zone_01
 └── line_01
```

The same spatial-object ID in two cameras represents two independent objects.

---

## 7. Zone Model

Conceptually:

```text
Zone
├── id
├── name
├── polygon
└── enabled
```

Supported geometry includes rectangles, triangles, arbitrary simple polygons, and valid concave polygons where supported.

---

## 8. Tripwire Model

Conceptually:

```text
Tripwire
├── id
├── name
├── start_point
├── end_point
├── direction
└── enabled
```

Direction may be:

```text
A_TO_B
B_TO_A
BOTH
```

Direction is camera-specific.

---

## 9. Zone State Machine

For each:

```text
camera_id + track_id + zone_id
```

the state machine is:

```text
OUTSIDE → OUTSIDE = no event
INSIDE  → INSIDE  = no event
OUTSIDE → INSIDE  = ZONE_ENTER
INSIDE  → OUTSIDE = ZONE_EXIT
```

Persistent occupancy does not generate repeated events.

---

## 10. Zone Boundary Hysteresis

The confirmed implementation uses:

```text
crossing_epsilon = 3.0 px
```

at the 1280×1280 reference resolution.

Behavior:

```text
distance to polygon boundary > 3 px
    → normal inside/outside decision

distance to polygon boundary <= 3 px
    → retain previous state
```

This prevents bounding-box jitter from generating rapid ENTER/EXIT oscillation.

The tolerance remains configurable.

---

## 11. Zone Hysteresis Validation

The deterministic suite `tests/test_zone_hysteresis.py` passed all 8 defined cases:

1. clearly outside
2. entering boundary band from outside
3. exactly on boundary
4. clearly inside
5. moving from inside into boundary band
6. repeated jitter around boundary
7. clearly outside after being inside
8. full boundary-jitter sequence

Result:

**8/8 tests passed.**

---

## 12. Tripwire Logic

Tripwire crossing is evaluated using track movement between trajectory/reference points.

The validated implementation uses:

- cross-product/side-of-line evaluation
- signed geometric distance
- finite line-segment intersection
- configured hysteresis

Parallel movement is rejected.

The infinite mathematical extension of a tripwire is not treated as the actual fence.

---

## 13. Crossing Direction & Duplicate Prevention

Directed crossings support:

```text
A_TO_B
B_TO_A
BOTH
```

A single physical crossing produces one logical event.

The track must move sufficiently away from the crossing region before another crossing can occur.

Jitter around a line must not generate repeated crossings.

---

## 14. Spatial Event Contract

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

Valid M5 events:

```text
ZONE_ENTER
ZONE_EXIT
LINE_CROSS
```

M5 does not produce `ALERT`, `INTRUSION`, `THREAT`, or `SUSPICIOUS` events.

---

## 15. Event Traceability & Ordering

Every event is traceable to:

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

The validated event ordering is deterministic:

```text
timestamp
→ track_id
→ spatial_object_id
```

If frame IDs are available in future revisions, they may be inserted after timestamp.

---

## 16. Track Lifecycle

### ACTIVE
Spatial state is evaluated normally.

### LOST
M5 does not automatically generate `ZONE_EXIT`.

### REMOVED
The object's spatial state is cleaned up without generating a false exit.

If a LOST track returns with the same M4 ID, its spatial context may continue. M5 does not perform re-identification.

---

## 17. Multi-Track & Multi-Camera Isolation

Spatial state is independent for each:

```text
camera + track + spatial object
```

Therefore one object's state cannot modify another object's state, and CAM01 geometry cannot affect CAM02.

---

## 18. Canonical Benchmark

The canonical benchmark asset is:

```text
videoplayback.mp4
```

The same benchmark should be reused across M3, M4, M5, and later applicable milestones.

Path resolution:

1. `IBVAP_TEST_VIDEO` environment variable, if defined.
2. Repository-relative fallback:
   `tests/assets/videoplayback.mp4`
3. Clear error if neither exists.

No developer-specific absolute path is permitted.

---

## 19. Real-Video Validation

The canonical traffic video was successfully processed.

Visual validation confirmed:

- vehicles entering the synthetic zone generate `ZONE_ENTER`
- vehicles leaving the zone generate `ZONE_EXIT`
- tripwire intersections generate `LINE_CROSS`
- track IDs remain consistent with M4
- spatial geometry aligns with tracked objects
- boundary hysteresis prevents rapid jitter-generated transitions

This is technical validation using traffic footage, not evidence of deployment performance in actual border conditions.

---

## 20. Final Frame Accounting

Final clean benchmark:

```text
total_received  = 1175
total_processed = 1175
total_dropped   = 0
```

Therefore:

```text
1175 = 1175 + 0
```

All benchmark frames were processed under the final benchmark conditions.

M2's bounded live-edge dropping behavior remains valid when a live workload exceeds available processing throughput.

---

## 21. Final Performance

Measured:

```text
Detector latency ≈ 20.36 ms
Tracker latency  ≈ 1.14 ms
Spatial latency  ≈ 0.34 ms
End-to-end        ≈ 22.07 FPS
```

The M5 spatial engine remains **sub-millisecond** and is not a computational bottleneck.

The 22.07 FPS figure is below the 25 FPS source rate, but the final clean benchmark still processed all 1175 frames with zero drops. Future real-time/multi-camera optimization can revisit total pipeline throughput separately from M5 correctness.

---

## 22. Active Tracks

At EOF:

```text
final_active_tracks = 0
```

This is expected because all tracks were finalized as `REMOVED` and their spatial state was cleared.

Future benchmark reports should additionally record:

```text
max_active_tracks
```

because final active tracks at EOF can naturally be zero.

---

## 23. Geometry & Edge-Case Testing

Validated cases include:

- inside
- outside
- exact boundary
- near boundary
- zone transitions
- tripwire crossing
- reverse crossing
- parallel movement
- boundary jitter
- multiple tracks
- multiple spatial objects

The zone hysteresis suite passed all 8 defined edge cases.

---

## 24. Benchmark Discipline

### Clean benchmark

Visualization disabled.

Used for authoritative performance measurements.

### Spatial validation

Visualization enabled.

Used for visual correctness.

Rendering overhead must not be mixed into the clean performance baseline.

---

## 25. Dependencies & Licensing

For every newly introduced dependency, record:

- exact package
- exact version
- license
- purpose
- runtime/development status

The same discipline applies to the existing Ultralytics/YOLO dependency in the M3 documentation.

---

## 26. Known Limitations

- Image-space geometry is affected by perspective.
- No camera calibration/homography is currently applied.
- Bounding-box jitter can affect the reference point.
- LOST tracks do not provide true physical-world position.
- Small/distant-object spatial decisions depend on M3/M4 quality.
- M5 does not estimate physical distance.
- M5 does not estimate physical speed.
- Synthetic zones on traffic footage do not represent real border geofences.

---

## 27. Future Improvements

Potential future work:

- interactive zone editor
- polygon drawing UI
- camera calibration
- perspective/homography
- advanced trajectory smoothing
- spatial event persistence
- improved adaptive hysteresis
- world-coordinate mapping

These are intentionally outside M5.

---

## 28. Final Acceptance Checklist

### Architecture
- [x] Spatial engine separated from detector/tracker
- [x] M4 `Track[]` consumed
- [x] `SpatialEvent[]` produced
- [x] Camera-specific configuration

### Zones
- [x] Polygon zones
- [x] Point-in-polygon
- [x] Zone entry
- [x] Zone exit
- [x] Occupancy state
- [x] Boundary hysteresis
- [x] Duplicate-event suppression

### Tripwires
- [x] Finite line segments
- [x] Crossing detection
- [x] Direction support
- [x] 3 px hysteresis
- [x] Parallel movement rejection
- [x] Duplicate-crossing prevention

### Lifecycle
- [x] LOST handling
- [x] REMOVED cleanup
- [x] Reappearance handling

### Isolation
- [x] Multi-track isolation
- [x] Multi-camera isolation

### Testing
- [x] Deterministic geometry tests
- [x] Zone hysteresis tests
- [x] Tripwire tests
- [x] Real-video validation
- [x] Visualization validation

### Performance
- [x] Detector latency measured
- [x] Tracker latency measured
- [x] Spatial latency measured
- [x] End-to-end latency/FPS measured
- [x] Frame accounting verified
- [x] Zero dropped frames in final clean benchmark

### Portability
- [x] Environment-variable video override
- [x] Repository-relative fallback
- [x] No developer-specific absolute benchmark path

### Scope
- [x] No alerting logic
- [x] No ANPR
- [x] No face recognition
- [x] No behavioral analytics
- [x] No suspicious-activity classification
- [x] No M6 implementation

---

# 29. Final Status

## 🟢 M5 — PASS / FROZEN

The two confirmed defects discovered during independent cross-verification were fixed:

1. **Zone boundary hysteresis**
2. **Hardcoded developer-specific benchmark path**

The corrected implementation was re-tested successfully.

The final M5 spatial overhead is approximately:

```text
0.34 ms
```

M5 is now frozen.

---

# 30. M6 Integration Boundary

M5 ends at:

```text
SpatialEvent[]
```

M6 begins by interpreting those events.

Example:

```text
M5:
Track 17
LINE_CROSS
Fence 01
A_TO_B

        ↓

M6:
Fence 01 = Restricted Boundary
Track 17 = Person
A_TO_B = Unauthorized Direction

        ↓

Security Event
        ↓
Alert
```

M5 must not implement this interpretation.

---

# 31. Next Milestone — M6

The next milestone is:

## M6 — Event Interpretation & Real-Time Alert Generation

M6 will consume:

```text
SpatialEvent[]
```

and begin converting spatial facts into meaningful security events.

Potential M6 capabilities:

- configurable event rules
- event severity
- event correlation
- alert generation
- alert deduplication
- event logging
- alert lifecycle
- configurable security policies

These are future responsibilities.

---

# 32. Final Instruction to Antigravity

M5 is **FROZEN**.

Do not modify M1–M5 while implementing future milestones unless a genuine, reproducible integration defect is discovered and explicitly documented.

Canonical pipeline:

```text
M2
 ↓
Frame
 ↓
M3
 ↓
Detection[]
 ↓
M4
 ↓
Track[]
 ↓
M5
 ↓
SpatialEvent[]
```

Future work begins at:

```text
SpatialEvent[]
 ↓
M6 Event Engine
```

Do not implement M6 inside M5.

Do not reopen completed M5 work without a reproducible defect.

**M5 COMPLETE. STOP.**
