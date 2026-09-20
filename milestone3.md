# IBVAP — Milestone 3
## Person & Vehicle Object Detection

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Development agent:** Google Antigravity  
**Milestone:** 3 — AI Object Detection / Perception Layer  
**Prerequisites:** Milestone 1 and Milestone 2 completed and validated  
**Current status:** Ready to implement

---

# 1. Purpose

Milestone 2 established a reliable video ingestion and frame-processing pipeline.

M3 also establishes the first **repeatable AI benchmarking protocol** for IBVAP. The same canonical surveillance clips should be reused across later milestones wherever applicable so that performance and detection-quality changes remain comparable over time.

Milestone 3 introduces the **first real AI capability** into IBVAP:

> Detect people and vehicles in video frames and convert the model output into standardized IBVAP `Detection` objects.

The pipeline should become:

Video Source
↓
Video Ingestion
↓
Frame
↓
Object Detector
↓
Detection[]
↓
Metrics / Visualization
↓
Future Tracking

At the end of this milestone, IBVAP must be able to take the real surveillance video used in Milestone 2 and identify relevant objects such as:

- Person
- Car
- Motorcycle
- Bus
- Truck

The detector must return structured detection information that Milestone 4 can consume.

---

# 2. Critical Scope Rule

This milestone is ONLY about **object detection**.

Do NOT implement:

- Multi-object tracking
- ByteTrack
- BoT-SORT
- Virtual fences
- Polygon zones
- Line crossing
- Intrusion detection
- Loitering
- Suspicious-activity detection
- Risk scoring
- ANPR
- OCR
- Face detection
- Face recognition
- Night-time enhancement
- Alert management
- Production dashboard
- Cross-camera identity
- Person re-identification
- TensorRT optimization
- NVIDIA DeepStream
- Distributed inference
- Custom training unless a later experiment explicitly requires it

Do not generate fake detections.

Do not create fake track IDs.

Do not label a detection as an event.

A detection means only:

> **An object of a particular class was detected at a particular location in a particular frame with a particular confidence.**

---

# 3. First Action — Inspect Milestone 1 and 2

Before changing anything:

1. Inspect the completed Milestone 1 architecture.
2. Inspect the completed Milestone 2 implementation.
3. Understand the existing `Frame` domain model.
4. Understand `CameraPipeline`.
5. Understand the current frame-consumer integration point.
6. Understand existing configuration.
7. Understand existing logging.
8. Understand existing metrics.
9. Understand existing tests.
10. Do not rewrite the video-ingestion system unless a genuine incompatibility is found.

The detector should plug into the existing pipeline.

The goal is:

**M2 remains responsible for video ingestion.  
M3 becomes responsible for AI perception.**

---

# 4. Target Architecture

The architecture should become:

Video Source
↓
Video Ingestion
↓
Frame
↓
Object Detector
↓
Detection[]
↓
Metrics / Optional Technical Visualization
↓
Future Tracker

Conceptually:

```text
┌──────────────────────┐
│   Video Source       │
│                      │
│ MP4 / Webcam / RTSP  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Video Ingestion      │
│      M2              │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│       Frame          │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   Object Detector    │
│        M3            │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│    Detection[]       │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Metrics / Validation │
└──────────┬───────────┘
           ↓
     Future M4 Tracker
```

The detector must not know how frames were captured.

---

# 5. Detector Must Be a Replaceable Component

Create a detector abstraction/interface.

The rest of IBVAP must not depend directly on a specific YOLO implementation.

Conceptually:

```text
BaseDetector
    │
    └── Concrete YOLO Detector
```

Future implementations could be:

```text
BaseDetector
├── YOLODetector
├── ONNXDetector
├── TensorRTDetector
└── FutureDetector
```

Do not implement all of these now.

Only establish the abstraction required for the current detector.

---

# 6. Model Selection

Use a mature pretrained object-detection model rather than training a detector from scratch.

The initial candidate may be the **Ultralytics YOLO ecosystem**, but do not treat the framework/model choice as permanent. The final choice must consider:

- detection quality
- real-time latency
- end-to-end throughput
- GPU memory
- small/distant-object performance
- deployment constraints
- model/software licensing

Do not select a model solely because it has the highest FPS.

The preferred first candidate is the **Ultralytics YOLO ecosystem**, because it provides:

- pretrained object detection
- GPU support
- convenient inference APIs
- common object classes
- strong real-time performance
- straightforward experimentation

However:

> Do not assume a model is good merely because it is YOLO.

The implementation must allow us to benchmark model size, inference speed, and detection quality.

Start with a lightweight/small pretrained model appropriate for real-time inference.

Do not immediately use a large model.

---

# 7. Model Weights

Use pretrained weights for the initial detector.

Record the licensing information for both the model/software and the weights where applicable.

At minimum record:

- model/framework license
- weights license or terms where applicable
- exact model version
- exact package/library version
- weights source
- model task
- input size
- precision
- device

Do not make a legal determination about whether a license is suitable for future commercialization, redistribution, or government deployment. Record the license and flag any implications for project/legal review before such deployment.

Also track the usage/license status of benchmark videos separately from model licensing. A video being available online does not automatically mean it is licensed for redistribution.

Do not train from scratch.

Do not download arbitrary weights from unknown sources.

The model and its version must be documented.

Record:

- model family
- exact model variant
- exact package/library version
- weights source
- model task
- input size
- precision
- device

If the chosen model is later changed, record the change.

---

# 8. Hardware / Device Selection

The development machine has an NVIDIA RTX 4060-class laptop GPU.

The detector should use GPU acceleration when CUDA is available.

The system must still have a controlled CPU fallback where practical.

At startup, report the selected device.

Conceptually:

```text
CUDA available?
    │
    ├── YES → GPU
    │
    └── NO  → CPU fallback
```

Do not hard-code a specific GPU name.

Do not assume that every deployment machine has an NVIDIA GPU.

---

# 9. CUDA Validation

Before running the full detector:

1. Verify that the Python environment can access the intended GPU.
2. Verify CUDA availability through the selected ML framework.
3. Confirm that the model can perform a small inference.
4. Confirm that GPU memory is being used when GPU mode is selected.
5. Report the device in the final milestone report.

If CUDA is unavailable:

- do not fake GPU usage
- report the issue
- allow CPU testing where practical

---

# 10. Detection Domain Contract

Use the `Detection` concept established in Milestone 1.

Each detection should represent one detected object in one frame.

At minimum, support:

- detection ID or internal identifier if needed
- camera/source ID
- frame ID
- timestamp
- class/category
- confidence
- bounding box

Do not add a `track_id` as though tracking already exists.

A future Milestone 4 tracker will assign track identities.

---

# 11. Bounding Box Representation

Choose one canonical internal representation.

The system should be able to represent:

- left/top/right/bottom coordinates

or an equivalent clearly documented format.

Be consistent throughout the project.

The coordinate system must be documented.

For example:

```text
(0,0)
  ┌──────────────────────→ X
  │
  │
  │
  ↓
  Y
```

Bounding boxes must remain traceable to the original frame dimensions.

---

# 12. Normalized vs Pixel Coordinates

The internal contract should make the coordinate convention explicit.

For the first implementation, pixel coordinates are acceptable and often easiest for visualization.

However, consider whether future zone/geometry processing will benefit from normalized coordinates.

If normalized coordinates are stored, document:

- range
- conversion method
- coordinate origin

Do not maintain multiple undocumented coordinate conventions.

---

# 13. Object Classes

Initially focus on surveillance-relevant classes.

Primary classes:

- Person
- Car
- Motorcycle
- Bus
- Truck

If the pretrained model uses a broader standard taxonomy, preserve its original class IDs internally where useful but expose a clean IBVAP semantic class.

For example:

```text
MODEL CLASS
      ↓
IBVAP OBJECT CLASS
      ↓
PERSON
```

Do not invent classes that the model cannot reliably detect.

---

# 14. Class Mapping

Create a clear mapping between model-specific labels and IBVAP labels.

This is important because a future detector may use different class IDs.

Conceptually:

```text
Model class ID
      ↓
Model class name
      ↓
IBVAP semantic class
```

This keeps the rest of the platform independent of YOLO/COCO-specific class numbering.

---

# 15. Confidence Threshold

Make the confidence threshold configurable.

Do not hard-code it permanently.

Begin with a sensible baseline such as approximately:

**0.25**

Then benchmark other values.

Potential experiments:

- 0.25
- 0.40
- 0.50
- 0.60

The exact final threshold must be based on validation results rather than preference.

---

# 16. Why Confidence Threshold Matters

Lower threshold:

- more detections
- potentially more false positives

Higher threshold:

- fewer detections
- potentially more false negatives

For surveillance, both matter.

We will eventually care about:

- missed people
- missed vehicles
- false detections
- confidence distribution

Do not choose a threshold merely because the screen "looks clean."

---

# 17. Input Resolution

The detector must have a configurable inference resolution where the selected model supports it.

Do not automatically run inference at the full source resolution.

Example:

Source:

1920×1080

Detector:

640×640 or another supported size

The model input resolution should be documented.

---

# 18. Initial Resolution Experiment

At minimum, evaluate a small set of inference sizes if the hardware permits.

Recommended baseline experiment:

- 640
- 768
- 960
- 1280, if the hardware can run it reasonably

Do not assume that 640 is sufficient for IBVAP.

Border surveillance differs from many ordinary indoor CCTV scenarios because relevant people and vehicles may occupy a very small portion of a high-resolution frame.

The purpose of the 1280 experiment is NOT to force a 1280 production configuration. It is to determine whether higher resolution materially improves small/distant-object detection enough to justify its computational cost.

The goal is to understand the tradeoff:

```text
Higher resolution
→ potentially better small-object detection
→ more computation
→ lower FPS

Lower resolution
→ faster
→ potentially weaker small-object detection
```

The final model configuration should be based on measurements.

---

# 19. Letterboxing / Preprocessing

Understand how the selected detector handles source frames that do not match the model's expected input aspect ratio.

Do not manually resize frames in a way that distorts object geometry unless the selected inference pipeline explicitly requires it.

Prefer the model/library's established preprocessing behavior.

Document:

- resizing
- padding/letterboxing
- normalization
- color conversion

Do not create unnecessary preprocessing layers.

---

# 20. Frame → Detection Integration

The detector should consume the M2 Frame object.

Conceptually:

```text
frame = pipeline.get_next_frame()

detections = detector.detect(frame)
```

The detector should return:

```text
Detection[]
```

Do not return raw model-specific result objects to the rest of the application.

Convert model output into IBVAP's internal Detection representation.

---

# 21. Camera and Timestamp Propagation

Every Detection must inherit the source information from its Frame.

For example:

```text
Frame
camera_id = CAM_TEST_01
timestamp = T

        ↓

Detection
camera_id = CAM_TEST_01
timestamp = T
```

Do not create detections without knowing which source they came from.

This is required later for events and evidence.

---

# 22. No Tracking Yet

A detection is not a track.

Example:

Frame 1:

```text
Person detected
```

Frame 2:

```text
Person detected
```

Frame 3:

```text
Person detected
```

M3 should NOT decide:

```text
Person #17
```

That is Milestone 4.

M3 only reports detections.

---

# 23. No Event Logic Yet

Do not interpret detections as:

- intrusion
- suspicious activity
- loitering
- alert
- threat

For example:

```text
Person detected inside image
```

does not mean:

```text
Intrusion
```

That interpretation belongs to future spatial/event intelligence.

---

# 24. No ANPR Yet

A vehicle detection should only produce:

```text
Vehicle detected
```

Do not attempt:

Vehicle
→ Plate
→ OCR
→ Number

ANPR is Milestone 8.

---

# 25. Detection Visualization

Create a minimal technical validation view.

It may show:

- source frame
- bounding boxes
- class labels
- confidence
- FPS
- inference latency

Example:

```text
┌───────────────────────────────────┐
│                                   │
│      ┌─────────────┐              │
│      │ Person      │              │
│      │ 0.91        │              │
│      └─────────────┘              │
│                    ┌────────────┐ │
│                    │ Car 0.87   │ │
│                    └────────────┘ │
│                                   │
├───────────────────────────────────┤
│ FPS: 27.4   Inference: 18 ms      │
└───────────────────────────────────┘
```

This is a technical validation tool, not the final dashboard.

---

# 26. Performance Metrics

Measure at least:

- model inference latency
- detection FPS
- end-to-end pipeline FPS
- source FPS
- dropped frames
- GPU memory usage if available
- GPU utilization if available
- CPU utilization if practical
- number of detections per frame

Keep M2 metrics separate from M3 metrics.

For example:

### M2

Frame ingestion latency

### M3

Model inference latency

### End-to-end

Frame ingestion → detection result

---

# 27. Important Performance Distinction

Do not report only:

> "YOLO runs at 100 FPS."

That may represent raw model inference under ideal conditions.

IBVAP cares about:

```text
Video source
↓
Frame capture
↓
Preprocessing
↓
Model inference
↓
Postprocessing
↓
Detection object creation
↓
Output
```

Measure both:

### Raw inference performance

and

### End-to-end detection pipeline performance

This distinction must appear in the final report.

---

# 28. Real-Time Target

Our Milestone 2 surveillance video runs at approximately 25 FPS.

For M3, the initial goal is:

> Maintain near-real-time processing for the tested surveillance video while producing useful person/vehicle detections.

Do not require a fixed 25 FPS detector if the model cannot achieve it.

Instead measure:

- inference FPS
- end-to-end FPS
- latency
- detection quality

If detection runs at 15 FPS while the source runs at 25 FPS, this may still be usable because M4 tracking can later bridge detector intervals.

However, persistent severe lag must be investigated.

---

# 29. Model Benchmarking

Evaluate at least two lightweight model configurations or model variants if practical.

Do not select the fastest model automatically.

The selection must consider the combined tradeoff between:

- detection quality
- small/distant-object recall
- inference latency
- end-to-end throughput
- GPU memory
- stability

A model that runs at 28 FPS but misses many distant people may be less suitable for IBVAP than a model that runs at 20 FPS with substantially better surveillance-relevant detection quality.

The purpose is not to benchmark every YOLO version.

We want enough information to select an appropriate baseline.

Record:

- model
- parameters if available
- input size
- precision
- device
- inference latency
- end-to-end FPS
- GPU memory
- qualitative detection behavior

The final model should be selected based on the project requirements.

---

# 30. Canonical IBVAP Benchmark Video Set

The project must establish a fixed benchmark set rather than selecting a new video for every milestone.

## Benchmark A — Primary Canonical Video

Use the real surveillance video already validated in Milestone 2:

**`013_883.mp4`**

Current known result from M2:

- Source FPS: 25 FPS
- Received FPS: approximately 24.74 FPS
- Processed FPS: approximately 24.75 FPS
- Average latency: approximately 39.69 ms
- Maximum latency: approximately 40.13 ms
- 433 frames received
- 411 frames processed
- Runtime frame drops after initialization: 0

Before finalizing M3, record and preserve the remaining source metadata if available:

- resolution
- duration
- codec/container
- total frame count
- file size
- source/license information

Do not replace Benchmark A simply because another video produces better results.

## Benchmark B — Secondary Scenario

Add a second representative surveillance video when available.

Prefer a different scene/camera perspective or environmental condition.

Record the same metadata.

## Benchmark C — Stress/Edge Scenario

Where available, add a clip containing one or more of:

- small/distant people
- small/distant vehicles
- heavy occlusion
- crowded scene
- low-light/night scene
- motion blur
- compression artifacts
- unusual camera angle

The purpose is to expose weaknesses, not to make the model look good.

## Benchmark Stability Rule

Where practical, use the same benchmark videos across M3, M4, M5 and later milestones.

Do not compare results from different videos as though they were directly equivalent.

If the benchmark set changes, document:

- what changed
- why it changed
- which historical results remain comparable

The canonical benchmark set should eventually be documented in a shared project benchmark/reference document.

# 31. Accuracy Evaluation

Do not claim "accuracy" merely from visual inspection.

For a proper evaluation, use a small manually annotated validation set or an appropriate public benchmark.

For the first M3 milestone, a lightweight project-specific validation set is acceptable.

Create/select representative frames containing:

- people
- cars
- motorcycles
- buses/trucks where available
- different distances
- partial occlusion
- different lighting
- different camera angles

Measure appropriate detection metrics where feasible.

Potential metrics:

- Precision
- Recall
- F1
- mAP
- per-class performance

Do not fabricate metrics.

---

# 32. Project-Specific Validation

The real downloaded surveillance video used in M2 should be reused for M3 validation.

The evaluation must specifically consider the border-surveillance small-object problem.

Look for:

- distant people occupying a small number of pixels
- distant vehicles
- partially visible people/vehicles
- objects near the edge of the frame

Compare suitable inference resolutions where practical.

Do not implement tiled inference or ROI inference in M3 merely because small-object performance is weak. Record the limitation and carry it into the future optimization plan.

The real downloaded surveillance video used in M2 should be reused for M3 validation.

Do not rely only on generic COCO benchmark numbers.

The question is:

> Does the detector work well on the kind of footage IBVAP is actually intended to process?

Evaluate representative frames from the actual surveillance video.

---

# 33. Difficult Conditions to Observe

While testing, pay attention to:

- small distant people
- partially occluded people
- groups of people
- dark scenes
- bright backlighting
- vehicles at distance
- motorcycles
- unusual camera angles
- compression artifacts
- motion blur

Do not try to solve all these problems in M3.

Record them.

They will guide later improvements.

---

# 34. Night Footage

If the downloaded video contains night footage, include it in validation.

Do not implement night enhancement yet.

The purpose is only to understand baseline detector performance.

Record observations such as:

- detection confidence drops
- small objects are missed
- false positives increase

Night-specific improvements belong to a later milestone.

---

# 35. Model Loading

The detector should load the model once and reuse it.

Do NOT load model weights for every frame.

Correct conceptual lifecycle:

Application starts
↓
Load model once
↓
Warm up if appropriate
↓
Process many frames
↓
Shutdown

This is critical for performance.

---

# 36. Warm-Up

If the selected inference framework benefits from warm-up:

- perform a small number of warm-up inferences
- exclude warm-up from steady-state FPS measurements
- clearly document warm-up behavior

Do not mix startup latency with normal inference latency.

---

# 37. Batch Inference

Do not introduce aggressive batching in M3 unless necessary.

For a single real-time camera:

single-frame inference is simpler and often more appropriate for latency.

Future multi-camera processing may investigate:

- small batches
- time-bounded batching
- GPU scheduling

Do not sacrifice real-time latency just to increase theoretical throughput.

---

# 38. Frame Scheduling

M2 already provides the frame pipeline.

Do not redesign it simply to make YOLO work.

If detector throughput is lower than source FPS:

- measure the behavior
- observe queue/drop behavior
- document the result

Do not introduce complicated frame skipping logic yet.

Adaptive inference will be considered later.

---

# 39. CPU Fallback

If CUDA is unavailable:

The detector should be capable of CPU inference if the selected library supports it.

The report must clearly state:

- GPU result
- CPU result if tested

Do not compare CPU and GPU results without specifying model/configuration.

---

# 40. Memory Management

Monitor GPU memory during inference where possible.

Avoid:

- loading multiple copies of the same model unnecessarily
- storing every frame indefinitely
- storing every detection result forever
- accidental accumulation of inference outputs

Only retain what the current milestone requires.

---

# 41. Error Handling

Handle:

- model loading failure
- missing weights
- unsupported device
- CUDA failure
- invalid frame
- unexpected model output
- inference exception

A model failure should be clearly reported.

Do not silently continue while pretending detections are valid.

---

# 42. Dependency Management

Add only the dependencies required for M3.

Do not install:

- DeepStream
- TensorRT
- multiple YOLO frameworks
- multiple OCR libraries
- multiple tracking libraries

unless specifically required for this milestone.

The detector implementation should use one primary framework.

---

# 43. Security / Model Source

Use trusted model/package sources.

Record the model version and package version.

Do not download arbitrary model files from unknown websites.

Do not commit large model weights into Git unless the repository strategy explicitly permits it.

Use a documented model/cache/download mechanism.

---

# 44. Logging

Add useful detector logs:

- model loaded
- model version/configuration
- selected device
- inference startup
- inference errors
- configuration changes

Do not log every detection at INFO level by default.

For debugging, a controlled DEBUG mode may expose more information.

---

# 45. Configuration

The following should be configurable:

- model path/name
- device
- confidence threshold
- inference size
- enabled classes
- visualization toggle
- benchmark mode where appropriate

Do not hard-code these values in multiple files.

---

# 46. Enabled Classes

Allow the detector configuration to limit classes.

For the first baseline:

- person
- car
- motorcycle
- bus
- truck

If the underlying model supports more classes, do not necessarily process every class.

Reducing unnecessary classes can simplify downstream processing.

---

# 47. Detection Output Example

A conceptual detection should contain information equivalent to:

```text
Detection
├── source/camera ID
├── frame ID
├── timestamp
├── object class
├── confidence
└── bounding box
```

It should NOT contain:

- track ID
- event ID
- alert ID
- risk score

Those belong to future layers.

---

# 48. Testing Plan

## Test A — Model loading

Verify:

- model loads
- correct device selected
- model can perform inference

---

## Test B — Single frame

Run inference on one known frame.

Verify:

- detections returned
- bounding boxes valid
- confidence values valid
- class mapping works

---

## Test C — Real surveillance video

Mandatory.

Run the existing M2 pipeline with the real downloaded surveillance video.

Verify:

- video remains stable
- detector receives valid frames
- detections are produced
- camera/source ID propagates
- timestamps propagate
- no fake results
- no uncontrolled memory growth

---

## Test D — Person detection

Verify representative people are detected.

Include, where available:

- near person
- distant person
- partially occluded person
- multiple people

---

## Test E — Vehicle detection

Verify representative vehicles.

Include where available:

- car
- motorcycle
- bus/truck
- distant vehicle
- partially occluded vehicle

---

## Test F — Different confidence thresholds

Evaluate at least a few thresholds.

Observe:

- detection count
- obvious false positives
- obvious missed detections

Do not select the final threshold only from one frame.

---

## Test G — Different inference sizes

If practical:

- 640
- 768
- 960

Compare:

- speed
- latency
- qualitative detection behavior

---

## Test H — GPU vs CPU

If practical:

- GPU benchmark
- CPU benchmark

Report the difference.

---

## Test I — Sustained processing

Run the detector for a meaningful continuous section of video.

Check:

- memory stability
- GPU memory stability
- FPS stability
- latency stability
- no accumulation of outputs

---

## Test J — Invalid frame

Verify that an invalid/unexpected frame does not crash the entire application unexpectedly.

---

# 49. Acceptance Criteria

M3 is complete only when:

### Detector architecture

- A detector abstraction exists.
- The concrete detector is isolated from the rest of the system.
- The detector consumes IBVAP `Frame` objects.
- The detector returns IBVAP `Detection` objects.
- Model-specific output does not leak into the rest of the application.

### Detection

- Person detection works.
- Vehicle detection works.
- Relevant vehicle classes are mapped correctly.
- Bounding boxes are correct.
- Confidence values are valid.
- Camera/source identity propagates.
- Frame identity propagates.
- Timestamp propagates.

### Performance

- Model loads once and is reused.
- GPU inference works when CUDA is available.
- M3 uses batch size 1 per camera.
- Inference latency is measured.
- End-to-end detection throughput is measured.
- Memory behavior is stable.
- Warm-up is excluded from steady-state benchmarks.
- Development performance thresholds are reported.
- Small/distant-object behavior is explicitly evaluated.
- Higher inference resolution is evaluated where hardware permits.

### Validation

- Real downloaded surveillance video is used.
- At least one representative person scenario is evaluated.
- At least one representative vehicle scenario is evaluated.
- Threshold behavior is evaluated.
- At least one model/input configuration benchmark is performed.
- No fabricated accuracy numbers are reported.

### Scope

Do NOT add:

- tracking
- ANPR
- face detection
- event detection
- intrusion
- alerts
- risk engine
- production dashboard

---

# 50. Definition of Done

Milestone 3 is complete when:

1. The detector abstraction is implemented.
2. A pretrained object-detection model is integrated.
3. The model loads once and performs inference.
4. CUDA/GPU inference works if available.
5. CPU fallback is handled where practical.
6. Frames from M2 are successfully passed to the detector.
7. Model outputs are converted to IBVAP Detection objects.
8. Person detections work.
9. Vehicle detections work.
10. Relevant vehicle classes are mapped.
11. Bounding boxes are valid.
12. Confidence values are valid.
13. Source/camera identity is preserved.
14. Frame identity is preserved.
15. Timestamps are preserved.
16. No track IDs are generated.
17. No events are generated.
18. No alerts are generated.
19. Real surveillance video is used for validation.
20. Detection latency is measured.
21. End-to-end FPS is measured.
22. GPU utilization/memory is measured where possible.
23. Model configuration is documented.
24. Threshold configuration is documented.
25. At least one model/configuration benchmark is completed.
26. The detector remains replaceable.
27. No fake detection output is used.
28. No unnecessary optimization framework is introduced.
29. Tests pass.
30. Antigravity stops after M3.

---

# 51. Required Final Report

After completing Milestone 3, STOP and provide a detailed report.

The report must contain:

## 1. Summary

What was implemented?

## 2. Model

Report:

- model family
- model/software license
- weights license/terms where applicable
- whether any deployment/redistribution review is recommended

Also report:

- model family
- exact variant
- model/package versions
- weights
- input resolution
- precision
- device

## 3. Detector architecture

Explain:

Frame
→ Detector
→ Detection[]

## 4. Detection contract

Explain all fields and coordinate conventions.

## 5. Class mapping

Report model classes → IBVAP semantic classes.

## 6. Configuration

Report:

- confidence threshold
- input size
- device
- enabled classes

## 7. Performance

Report:

- source FPS
- inference latency
- end-to-end latency
- inference FPS
- end-to-end FPS
- dropped frames
- GPU utilization if available
- GPU memory if available
- CPU usage if available

Clearly separate:

**raw model performance**

from:

**full pipeline performance**

## 8. Benchmark results

Compare tested model/configuration variants.

## 9. Benchmark videos

Report the exact benchmark clips used.

At minimum identify:

- Benchmark A: `013_883.mp4`
- any Benchmark B/C clips
- resolution
- FPS
- duration
- codec/container where available
- source/license information

Clearly state whether the same benchmark files are intended for future M4/M5 comparisons.

## 10. Validation

Describe results on the real surveillance video.

Include observations for:

- people
- vehicles
- distant objects
- occlusion
- lighting where available

## 11. Accuracy evaluation

If quantitative evaluation was performed, report the actual methodology and results.

If no formal ground-truth dataset was created, explicitly say so.

Never invent accuracy percentages.

## 12. Problems encountered

Report:

- installation issues
- CUDA issues
- model issues
- frame compatibility issues
- performance bottlenecks

## 13. Known limitations

Be honest.

Examples:

- small/distant objects
- night performance
- occlusion
- false positives
- CPU performance

## 14. Future optimization

Explain what could later improve performance:

- FP16
- ONNX
- TensorRT
- DeepStream
- adaptive inference
- ROI processing
- batching

Do not implement these unless explicitly requested.

## 15. M4 integration

Explain exactly how Milestone 4 will consume the Detection objects.

The expected next flow is:

Frame
↓
Detector
↓
Detection[]
↓
Tracker
↓
Track[]

## 16. Next milestone

State that Milestone 4 will introduce multi-object tracking.

Then STOP.

---

# 52. Important Future Architecture

After M3, the intended system becomes:

```text
                    VIDEO
                      ↓
                M2 INGESTION
                      ↓
                    FRAME
                      ↓
              M3 OBJECT DETECTOR
                      ↓
                 DETECTION[]
                      ↓
               M4 TRACKER
                      ↓
                  TRACK[]
                      ↓
          M5 SPATIAL INTELLIGENCE
                      ↓
               M6 EVENT ENGINE
                      ↓
              M7+ BEHAVIOR
                      ↓
              RISK / ALERTS
```

Do not skip directly from detection to events.

Tracking is necessary because later behavior such as:

- loitering
- movement direction
- zone crossing
- trajectory analysis

requires temporal object identity.

---

# 53. Why M3 Must Stay Simple

M3 is deliberately limited.

We want to answer one question:

> **Can IBVAP reliably turn surveillance frames into useful, structured person/vehicle detections at real-time or near-real-time speed?**

If the answer is yes, M3 succeeds.

Only then should we add tracking.

Do not hide detection problems by adding tracking, event rules, or complicated post-processing.

---

# 54. Engineering Principles

These rules continue from M1 and M2.

1. Use real model output.
2. Never fabricate detections.
3. Never fabricate accuracy.
4. Measure before optimizing.
5. Keep the detector replaceable.
6. Keep model-specific details inside the perception layer.
7. Keep tracking separate from detection.
8. Keep event logic separate from perception.
9. Preserve source and timestamp information.
10. Avoid unnecessary frame copies.
11. Load the model once.
12. Keep GPU use measurable.
13. Do not optimize for benchmark FPS at the expense of useful detection quality.
14. Prefer a balanced accuracy/latency tradeoff.
15. Do not introduce production-scale infrastructure prematurely.
16. Test on real surveillance footage, not only synthetic data.
17. Do not automatically continue to M4.

---

# 55. Final Instruction to Antigravity

Implement **Milestone 3 only**.

Start by inspecting and preserving the completed Milestone 1 and Milestone 2 architecture.

Integrate a pretrained object detector through a clean detector abstraction.

Use GPU acceleration on the development machine when available.

Use the real downloaded surveillance video already used for M2 (`013_883.mp4`) as the mandatory primary validation source.

Treat `013_883.mp4` as Canonical Benchmark A for future milestone comparisons.

Use batch size 1 per camera.

Evaluate the border-surveillance small-object problem explicitly and test a higher inference resolution such as 1280 where hardware permits.

Record model/software and weight licensing information without making unsupported legal conclusions.

Produce standardized IBVAP `Detection` objects containing the required object, bounding-box, confidence, source, frame, and timestamp information.

Measure both model-level and end-to-end performance.

Benchmark sensible model/input configurations where practical.

Do not implement tracking or any downstream surveillance intelligence.

Do not implement ANPR, face detection, event detection, alerts, risk scoring, or production dashboard functionality.

Do not fabricate accuracy or performance numbers.

Do not introduce TensorRT, DeepStream, or other advanced optimization frameworks in this milestone unless a concrete blocking issue makes one unavoidable.

At the end, provide the complete final report specified in this document.

**STOP after Milestone 3.**

Do not automatically begin Milestone 4.
