# IBVAP — Milestone 2
## Video Ingestion & Frame Processing Pipeline — Revised Specification

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Development agent:** Google Antigravity  
**Milestone:** 2 — Video Ingestion, Frame Lifecycle, Buffering, Concurrency, Monitoring, and Reliability  
**Prerequisite:** Milestone 1 completed and validated

---

# 1. Purpose of This Milestone

Milestone 1 established the architectural foundation of IBVAP.

Milestone 2 is the first milestone in which the system processes real video.

The objective is to build a reliable, modular, low-latency **video ingestion and frame-processing pipeline** that future AI modules can consume.

The final system must eventually support:

- Downloaded CCTV/video recordings
- Webcam/live video
- RTSP IP cameras
- Multiple simultaneous cameras
- Continuous real-time processing
- Low-latency frame handling
- Camera disconnection/reconnection
- Frame statistics
- Failure isolation
- Future hardware-accelerated video decoding

For the current development environment, we **do not have access to a physical CCTV/IP camera or a known public RTSP stream**.

Therefore:

### Mandatory in Milestone 2

1. Real downloaded video files must be used for validation.
2. The architecture must support future live sources.
3. Webcam support should be prepared and tested if a webcam is available.
4. RTSP support must be architecturally prepared but must NOT be falsely marked as tested when no RTSP source exists.

A real downloaded CCTV/surveillance recording is an acceptable and important test source for this milestone and all later AI milestones.

---

# 2. Critical Scope Rule

Do NOT implement:

- YOLO
- Person detection
- Vehicle detection
- Object tracking
- Face detection
- Face recognition
- ANPR
- OCR
- Intrusion detection
- Virtual fences
- Loitering
- Suspicious-activity detection
- Risk scoring
- Production alert engine
- Full surveillance dashboard
- TensorRT optimization
- NVIDIA DeepStream
- Distributed processing
- Kafka/RabbitMQ/etc. unless a concrete requirement proves one is necessary

Do not create fake detections or fake alerts.

The only goal is:

**Video Source → Frame Ingestion → Frame Processing → Monitoring/Validation**

---

# 3. Development Source Strategy

Because no physical CCTV camera is currently available, development will use three source categories.

## Source A — Downloaded CCTV / Surveillance Video

This is the **primary mandatory validation source**.

Use real downloaded surveillance footage where possible.

Preferred characteristics:

- 720p or 1080p
- 15–30 FPS if available
- daylight and/or night footage
- people/vehicles where possible
- realistic camera perspective
- several minutes of continuous footage
- different resolutions/codecs where practical

The source may be:

- MP4
- MKV
- AVI
- another format supported by the selected decoder

The exact videos used must be documented.

Do not claim that downloaded video is equivalent to a live RTSP camera. It is a test source for the same downstream frame-processing architecture.

---

## Source B — Webcam / Live Local Source

If a webcam is available on the development machine:

- test live capture
- measure actual FPS
- verify continuous frame acquisition
- test clean shutdown

If no webcam is available:

- do not block the milestone
- document that live webcam testing was unavailable

The architecture must still support this source type.

---

## Source C — RTSP IP Camera

There is currently no physical CCTV/RTSP source available.

Therefore:

- RTSP support must be architecturally prepared.
- Do not claim RTSP integration is validated.
- Do not depend on an unknown public stream.
- Do not use a random public RTSP URL without verifying its legality, stability, and suitability.
- Do not make RTSP testing a blocker for Milestone 2.

A future local RTSP test environment may be created using a locally hosted RTSP server such as MediaMTX with a prerecorded video as the source. That is a future validation option, not a requirement for this milestone.

When actual RTSP testing becomes available, it must be treated as a separate live-source validation stage.

---

# 4. First Action — Inspect Milestone 1

Before implementing anything:

1. Inspect the completed Milestone 1 architecture.
2. Understand the existing module boundaries.
3. Reuse the domain contracts already established.
4. Do not unnecessarily redesign Milestone 1.
5. Identify the intended location for video ingestion.
6. Identify the intended Frame domain contract.
7. Identify existing logging/configuration/error-handling infrastructure.
8. Preserve existing conventions unless there is a strong engineering reason to change them.
9. Check the existing dependency strategy before adding new packages.

If Milestone 1 contains an architectural problem that prevents this milestone from being implemented correctly, document it and make the smallest justified correction.

Do not perform a broad rewrite.

---

# 5. Target Architecture

The immediate pipeline should conceptually be:

Video Source
↓
Video Source Manager
↓
Decoder / Capture Layer
↓
Frame Acquisition
↓
Bounded Frame Buffer
↓
Frame Processing
↓
Frame Metadata / Metrics
↓
Future AI Inference

The architecture should eventually support:

                         ┌── Video File
                         │
Video Source ────────────┼── Webcam
                         │
                         └── RTSP IP Camera
                              ↓
                       Video Ingestion
                              ↓
                       Frame Pipeline
                              ↓
                    Future AI Perception

The downstream AI modules must not care whether a frame came from:

- an MP4
- a webcam
- an RTSP camera

They should receive the same internal frame representation.

---

# 6. Video Source Abstraction

Create a generic concept for a video source.

A source should have:

- stable identity
- source type
- configuration
- lifecycle state
- runtime statistics
- error state where applicable

Potential source types:

- FILE
- WEBCAM
- RTSP

The FILE source is mandatory and must be fully operational.

WEBCAM should be implemented and tested if hardware is available.

RTSP should be structurally supported but does not need to be declared production-tested in this milestone.

Adding a new source type later should not require rewriting downstream frame-processing or AI modules.

---

# 7. Camera and Source Relationship

The final IBVAP platform is camera-centric.

Every stream should eventually be associated with a Camera identity.

Conceptually:

Camera
├── camera_id
├── name
├── location
├── source configuration
├── status
└── stream

For downloaded videos, create a test-source identity representing the simulated camera.

For example:

Downloaded recording
→ simulated camera/source ID
→ Frame

This allows all future AI processing to behave as though the frame came from a camera without pretending that a real camera exists.

Every frame must retain source/camera identity.

---

# 8. Frame Domain Object

Use the Frame concept established in Milestone 1.

A frame should carry both image data/reference and metadata.

At minimum, the architecture should support:

- frame identifier/index
- source/camera identifier
- timestamp
- width
- height
- frame data/reference
- source information where useful

Potential future metadata:

- source FPS
- capture timestamp
- ingestion timestamp
- processing timestamp
- sequence information
- decoding information

Do not overload the Frame object with unrelated AI information.

Future detections should remain separate objects.

---

# 9. Timestamp Handling

Timestamp correctness is important for surveillance.

Every captured frame should have a meaningful timestamp.

Distinguish conceptually between:

### Source timestamp

Timestamp associated with the video source/frame if available.

### Ingestion timestamp

When IBVAP receives the frame.

### Processing timestamp

When a processing stage handles the frame.

For a prerecorded video, source time may represent the video's timeline rather than actual wall-clock time.

For a live source, ingestion time becomes important.

Do not pretend that a prerecorded video's timestamp is the current real-world time.

The architecture should support both concepts.

---

# 10. Frame Numbering

Maintain frame sequencing where possible.

For a video source:

Frame 1
Frame 2
Frame 3
...

Frame numbering is useful for:

- debugging
- dropped-frame measurement
- synchronization
- performance analysis
- future AI debugging

If a decoder cannot provide meaningful source frame numbering, generate an internal monotonically increasing frame sequence.

---

# 11. Video File Support — Mandatory

Fully implement video-file ingestion first.

The system must be able to:

1. Receive a configured video-file source.
2. Open the source.
3. Validate that it can be decoded.
4. Read frames continuously.
5. Create the internal Frame representation.
6. Send frames into the processing pipeline.
7. Track source metadata.
8. Report statistics.
9. Detect end-of-file.
10. Close resources cleanly.

Test with at least one real downloaded surveillance/CCTV-style video.

Preferably test more than one file with different:

- resolutions
- FPS
- codecs/containers
- durations

Do not assume that every video has identical characteristics.

---

# 12. Video File Playback Modes

The ingestion architecture should distinguish between:

### Real-time simulation mode

Process the downloaded video according to its source timing.

Example:

30 FPS recording
→ approximately 30 FPS playback/ingestion

This is useful for testing real-time behavior.

### Maximum-throughput mode

Process as fast as the pipeline can safely consume.

This is useful for benchmarking raw processing capability.

The mode should be configurable.

Do not confuse maximum-throughput FPS with real-time FPS.

A system processing a prerecorded file at 120 FPS does not mean it can necessarily process a live 120 FPS CCTV stream.

---

# 13. Webcam / Live Video

If a webcam is available:

- connect
- capture
- create Frame objects
- measure FPS
- validate timestamps
- test clean shutdown

If no webcam is available:

- leave the source abstraction ready
- document that hardware validation was not possible

The downstream processing pipeline must remain identical.

---

# 14. RTSP — Explicitly Deferred Hardware Validation

There is currently no physical CCTV camera or known public RTSP stream available.

Therefore, for Milestone 2:

### Required

- RTSP source abstraction
- RTSP configuration representation
- lifecycle states
- error handling design
- reconnection design
- clean interface for future implementation/testing

### Not required

- production RTSP validation
- physical CCTV testing
- public RTSP testing
- remote camera authentication testing

### Future validation options

When needed, use one of:

1. A real IP CCTV camera.
2. A controlled local RTSP server such as MediaMTX.
3. A prerecorded surveillance video published as a local RTSP stream using an appropriate test setup.

A local RTSP simulation is preferred over an unknown public stream because it is:

- deterministic
- reproducible
- controllable
- legally safer
- easier to debug

Do not claim that RTSP is fully validated until a real streaming protocol test has actually been performed.

---

# 15. Decoder Technology Decision

For Milestone 2, **OpenCV VideoCapture is acceptable and preferred for the initial implementation** because:

- it is simple
- it is mature
- it integrates naturally with Python/OpenCV pipelines
- it is sufficient for downloaded-video validation
- it keeps Milestone 2 focused

Do not build a custom FFmpeg pipeline just for theoretical future performance.

However, the architecture must not make OpenCV VideoCapture an irreversible dependency.

Future live/production stages may require:

- FFmpeg
- GStreamer
- NVIDIA hardware decoding
- NVIDIA DeepStream

Especially for:

- many simultaneous RTSP cameras
- hardware decoding
- low-latency transport control
- GPU-resident pipelines
- large-scale deployment

Therefore:

**Milestone 2 = OpenCV-first ingestion.**

**Future optimization = evaluate FFmpeg/GStreamer/DeepStream based on measured requirements.**

---

# 16. RTSP Transport Considerations for Future

Do not implement these unless actual RTSP support is being tested.

Future RTSP configuration may need:

- TCP vs UDP transport
- connection timeout
- read timeout
- reconnect interval
- exponential backoff
- authentication
- buffer size
- latency policy

Document these as future requirements.

Do not invent a production configuration without testing.

---

# 17. Bounded Frame Buffer

This is a mandatory requirement.

The initial default frame-buffer capacity should be:

**3 frames per source.**

This is a starting baseline, not a permanent production value.

Make the buffer size configurable.

Allow future tuning to values such as:

- 2
- 3
- 5
- 10

based on measured latency and processing behavior.

Do not choose an arbitrarily huge queue.

The reason for the small default is that real-time surveillance should prioritize current frames over accumulating historical frames.

---

# 18. Frame Buffer Overflow Policy

When the buffer reaches capacity:

Do NOT allow unlimited growth.

The default policy should prioritize the newest frame and prevent stale-frame accumulation.

The exact implementation can use an appropriate bounded queue strategy, but it must satisfy:

- fixed maximum capacity
- no unbounded memory growth
- measurable dropped-frame count
- low-latency behavior
- predictable overflow behavior

Document the selected policy.

---

# 19. Why Small Buffers Matter

Suppose:

Source = 30 FPS

Processing = 10 FPS

With a 1000-frame queue, the application can eventually process very old footage.

With a small bounded queue, stale frames are discarded and the system remains close to the live edge.

For surveillance:

**Low latency > processing every frame.**

However, do not blindly assume that 3 frames is optimal forever.

Future milestones will benchmark different buffer sizes.

---

# 20. Capture and Processing Must Be Decoupled

Do not tightly couple:

Capture → Process → Capture → Process

Instead establish:

Capture
↓
Bounded Buffer
↓
Processing

This allows the capture stage to continue receiving the latest available frame while processing consumes frames independently.

Later the architecture can expand into:

Capture
↓
Frame Buffer
├──→ AI inference
├──→ display
└──→ monitoring

Do not implement all branches now.

---

# 21. Concurrency Model

Python is the expected implementation language for the AI/backend pipeline.

Do not arbitrarily choose between:

- threading
- asyncio
- multiprocessing

without considering the workload.

For Milestone 2:

### Requirement

Select and implement a concurrency model appropriate for:

- continuous frame capture
- frame buffering
- processing
- future GPU inference
- multiple future camera sources

The selected approach must be justified.

Antigravity should consider:

### Threads

Useful for I/O-oriented capture and simple producer/consumer pipelines.

Potential concern:

- Python GIL for CPU-bound Python work

However, native video decoding libraries may release the GIL for substantial operations.

### Asyncio

Useful for:

- network orchestration
- APIs
- event-driven services

Not automatically the best choice for CPU-heavy frame processing.

Do not force the entire video pipeline into asyncio merely because the backend may use async APIs.

### Multiprocessing

Can isolate workloads and bypass the GIL.

Potential concerns:

- frame serialization/copying
- memory overhead
- complexity

Do not use multiprocessing simply because it sounds more parallel.

---

# 22. Concurrency Decision Requirement

Antigravity must:

1. Select the initial concurrency approach.
2. Explain why it was selected.
3. Explain why alternatives were not selected for this milestone.
4. Keep the design replaceable enough for future optimization.
5. Avoid premature distributed architecture.

The final report must explicitly state:

- concurrency model
- producer/consumer design
- synchronization mechanism
- expected bottleneck
- future migration path if performance becomes insufficient

---

# 23. Single-Source First, Multi-Source Ready

Do not overcomplicate Milestone 2 with many cameras.

First prove:

**one source → reliable frame pipeline**

Then ensure the architecture can eventually support:

CAM01 → independent pipeline

CAM02 → independent pipeline

CAM03 → independent pipeline

Do not implement complex multi-camera scheduling yet.

---

# 24. Camera Failure Isolation

This requirement is critical.

If:

CAM-001 fails

it must not automatically crash:

CAM-002
CAM-003
CAM-004

The architecture should allow independent source/pipeline contexts.

For Milestone 2, demonstrate the principle where practical using independent source instances or tests.

---

# 25. Reconnection Strategy

For future live sources, especially RTSP:

STREAMING
↓
DISCONNECTED
↓
RECONNECTING
↓
STREAMING

Do not implement an uncontrolled infinite retry loop.

Future configuration should support:

- retry interval
- backoff
- maximum attempts
- source timeout

For the downloaded-file source, EOF is a normal termination condition, not a reconnection condition.

---

# 26. Processing Model

The processing pipeline should behave as a continuous stream.

Conceptually:

Source active
↓
Frame acquired
↓
Frame enters bounded buffer
↓
Processor consumes frame
↓
Metrics update
↓
Frame becomes available to future consumers

Do not make each frame a REST request.

Do not design the core video pipeline around HTTP request/response.

---

# 27. Frame Dropping Policy

The system must explicitly define what happens when processing cannot keep up.

Default behavior:

- bounded queue
- prioritize current frames
- discard stale frames when necessary
- record dropped-frame metrics
- prevent unbounded latency

Do not silently skip frames without measurement.

---

# 28. FPS Metrics

Implement real performance metrics.

At minimum distinguish:

### Source FPS

The expected/declared FPS of the source.

### Received FPS

How quickly frames are being acquired.

### Processed FPS

How quickly the processing stage consumes frames.

### Dropped Frames

Number of frames discarded due to buffering/overload according to the selected policy.

### Processing latency

Time between ingestion and processing completion where measurable.

Also consider:

- queue depth
- average latency
- recent-window latency
- maximum observed latency

Do not report synthetic metrics.

---

# 29. Latency Measurement

Measure latency where possible.

For a prerecorded file, distinguish:

### Pipeline processing latency

How long IBVAP takes to process a frame.

### Playback/source-time lag

Difference between simulated source timing and processing timing.

For live sources, eventually:

capture time
→ processing
→ output

should allow end-to-end latency measurement.

Do not confuse high benchmark throughput on a file with low live latency.

---

# 30. Performance Baseline

Milestone 2 must establish a baseline before AI inference.

The baseline is a **development target**, not a final production specification.

For a 1080p downloaded video on the development machine:

### Target

- Decode/processing should ideally sustain at least the source's nominal FPS for a normal 24–30 FPS video in real-time simulation mode.
- Processed FPS should preferably be ≥ 24 FPS for a 30 FPS source.
- Dropped frames should normally remain near 0 under normal processing load.
- Recent pipeline latency should preferably remain below approximately 200 ms in the basic pipeline.
- Queue depth should normally remain near empty during a healthy real-time run.

### Concerning result

Flag results for investigation if:

- processed FPS persistently falls below ~15 FPS for a 24–30 FPS source
- dropped frames are continuously increasing under normal load
- latency persistently exceeds ~500 ms
- queue remains close to maximum capacity
- CPU usage is unexpectedly high for simple decode/processing
- memory usage grows continuously

These thresholds are not "failure = project rejected" numbers.

They are engineering signals that tell us whether optimization needs investigation.

---

# 31. Maximum-Throughput Benchmark

Also support a benchmark mode where the downloaded video is processed as quickly as possible.

Record:

- total frames
- total processing time
- average FPS
- peak/average memory if practical
- CPU utilization if practical

This gives us two different measurements:

### Real-time capability

Can we keep up with the source?

### Maximum throughput

How fast can the current pipeline process frames?

Do not use maximum-throughput FPS as a claim about live CCTV capability.

---

# 32. Performance Report Format

The final report should contain a table similar in meaning to:

Metric | Result | Interpretation

Source resolution | actual | video properties

Source FPS | actual | nominal rate

Received FPS | actual | capture performance

Processed FPS | actual | pipeline throughput

Dropped frames | actual | overload indicator

Average latency | actual | responsiveness

Maximum latency | actual | worst observed delay

CPU usage | actual if available | resource usage

Memory usage | actual if available | stability

The exact formatting can differ.

---

# 33. Preview / Validation Interface

Create only a minimal technical validation interface.

Its purpose is to prove:

- frames are arriving
- frames are valid
- dimensions are correct
- timestamps advance
- frame numbers advance
- FPS is measurable
- processing is occurring
- dropped frames are measurable
- shutdown works

A simple preview window or technical validation page is acceptable.

Do not create the final IBVAP command-center dashboard.

---

# 34. No Fake Surveillance UI

Do not build polished UI containing fake:

- people
- vehicles
- alerts
- ANPR
- risk levels
- tracking IDs

At this stage, technical validation is more important than appearance.

The final dashboard will be created after the intelligence pipeline exists.

---

# 35. Error Handling

Handle at least:

### Source cannot open

- clear error
- source identity
- no application-wide crash

### Invalid video

- clear diagnostic
- graceful failure

### End of file

- normal completion state
- resource cleanup

### Decode failure

- appropriate error handling
- diagnostic logging
- no uncontrolled loop

### Processing overload

- bounded queue
- dropped-frame measurement
- latency monitoring

### Application shutdown

- graceful termination
- resource release

---

# 36. Resource Cleanup

When a source stops:

- release capture resources
- stop workers
- close queues/resources as appropriate
- stop metrics processing
- release file/stream handles
- leave the system in a clean state

Repeated start/stop operations should not continuously leak resources.

---

# 37. Structured Logging

Use the logging foundation from Milestone 1.

Important runtime events should include:

- source opened
- source closed
- source failure
- source state change
- frame decode failure
- buffer overflow/drop
- processing slowdown
- worker shutdown
- recovery attempt

Logs should identify the relevant source/camera where applicable.

Do not flood logs with one message for every normal frame unless running in an explicit debug mode.

---

# 38. Configuration

Do not hard-code important runtime settings.

At minimum, prepare configuration for:

- source
- source type
- buffer capacity
- playback mode
- frame handling policy
- logging level
- metrics settings

Initial buffer default:

**3 frames**

Make it configurable.

Do not require a code change just to change buffer size.

---

# 39. Dependency Strategy

Do not install every possible video library.

For Milestone 2:

### Preferred initial implementation

- Python
- OpenCV

Use the project's existing environment/dependency strategy from Milestone 1.

OpenCV's VideoCapture is acceptable for:

- downloaded video
- webcam
- initial source abstraction

Do not add FFmpeg Python bindings merely because FFmpeg may be useful later.

---

# 40. Future Decoder Evolution

Document this future progression:

### Stage 1 — Current

OpenCV VideoCapture

Good for:

- development
- downloaded videos
- webcam
- basic validation

### Stage 2 — Live stream testing

Evaluate FFmpeg/GStreamer if RTSP requirements expose limitations.

### Stage 3 — Multi-camera production

Evaluate:

- hardware decode
- GStreamer
- NVIDIA DeepStream

### Stage 4 — High-performance deployment

Potential:

- GPU-resident video pipelines
- hardware decoding
- optimized inference
- TensorRT
- DeepStream

Do not implement future stages now without evidence of need.

---

# 41. Downloaded CCTV Video Dataset for Development

Because no CCTV hardware is available, build the project around a reusable local test-video collection.

The project should support a clear local test-data directory or equivalent configuration mechanism.

Potential categories:

- daylight
- nighttime
- people
- vehicles
- crowded
- low-light
- static scene
- moving camera if relevant

Do not commit large copyrighted videos into Git.

Document where each test video came from and its permitted use where appropriate.

---

# 42. Recommended Test Video Characteristics

At least one test video should ideally have:

- 720p or 1080p
- 20–30 FPS
- continuous footage
- people and/or vehicles
- fixed surveillance-style viewpoint

Later, before AI validation, collect additional videos representing:

- person movement
- vehicle movement
- nighttime conditions
- restricted-area scenarios

The exact datasets will be selected more carefully in future AI milestones.

---

# 43. No Need for a Physical CCTV Camera Yet

Do not treat the absence of a physical CCTV camera as a blocker.

The majority of the future perception pipeline can be developed using:

Downloaded CCTV video
→ Frame
→ Detection
→ Tracking
→ Event engine

The input abstraction ensures that later we can replace:

Downloaded video

with:

RTSP camera

without rewriting the downstream AI/event architecture.

This is intentional.

---

# 44. Future Local RTSP Simulation

When RTSP validation becomes important, a reproducible local setup may be used.

Conceptually:

Downloaded CCTV video
↓
Local RTSP server such as MediaMTX
↓
RTSP stream
↓
IBVAP RTSP source
↓
Frame pipeline

This allows us to test:

- RTSP connection
- disconnect
- reconnect
- latency
- buffering
- source lifecycle

without requiring physical CCTV hardware.

Do not make this part of Milestone 2 unless Antigravity can implement and validate it cleanly without expanding scope.

---

# 45. Future AI Integration Point

Milestone 2 must expose a clean location where Milestone 3 will attach object detection.

Future:

Frame
↓
Object Detector
↓
Detection[]

The detector receives the established Frame representation.

The detector must not need to know:

- how the video was opened
- whether it came from MP4/webcam/RTSP
- how the frontend works
- how the database works

This separation is mandatory.

---

# 46. Future Performance Architecture

Keep the architecture compatible with a future high-performance pipeline:

IP Cameras
↓
Hardware Decode
↓
Frame Scheduler
↓
Bounded Buffers
↓
GPU Inference
↓
Tracking
↓
Event Engine
↓
Async Event Queue
↓
Database / Evidence / Alerts
↓
Dashboard

Future optimization may include:

- GPU hardware decoding
- FP16 inference
- TensorRT
- NVIDIA DeepStream
- adaptive frame rates
- ROI processing
- detection/tracking separation
- multi-camera batching
- camera prioritization
- asynchronous event processing

None of these are Milestone 2 requirements.

---

# 47. Testing Requirements

## Test A — Normal downloaded CCTV video

Mandatory.

Verify:

- source opens
- metadata is read
- frames arrive
- frame numbers advance
- timestamps advance
- dimensions are correct
- FPS is measured
- frames are processed
- source closes cleanly

---

## Test B — Different video properties

Where possible, test at least one additional file with different:

- resolution
- FPS
- container/codec

Verify that the pipeline does not depend on one exact video format.

---

## Test C — Invalid/missing file

Verify:

- clear error
- no application-wide crash
- resources remain clean

---

## Test D — End-of-file

Verify:

- EOF is distinguished from failure
- resources are released
- workers stop correctly

---

## Test E — Slow processing

Create a controlled processing bottleneck.

Verify:

- queue does not grow indefinitely
- buffer remains bounded
- stale frames are dropped according to policy
- dropped-frame count increases
- latency does not grow without bound

---

## Test F — Start/stop

Start and stop the source repeatedly.

Verify:

- resources are released
- workers terminate
- no obvious accumulation of resources
- pipeline can restart cleanly

---

## Test G — Webcam

If available:

- connect
- capture
- measure FPS
- stop cleanly

If unavailable:

- document as untested

---

## Test H — RTSP

Not mandatory for Milestone 2 because no RTSP source is currently available.

If Antigravity creates a local RTSP test setup without expanding scope, it may be tested.

Otherwise report:

**RTSP architecture prepared; live RTSP validation deferred because no source is currently available.**

Do not mark this as a failure.

---

# 48. Acceptance Criteria

Milestone 2 is complete only when:

### Architecture

- Video ingestion is separated from AI inference.
- Frame representation is stable and documented.
- Source types are abstracted.
- Camera/source identity can be propagated to frames.
- Capture and processing responsibilities are separated.
- Concurrency strategy is documented.

### Reliability

- Invalid sources are handled gracefully.
- EOF is handled correctly.
- Resources are released.
- Errors are logged.
- Future camera failures can be isolated.

### Real-time behavior

- Buffering is bounded.
- Initial buffer default is 3 frames.
- Buffer size is configurable.
- Stale frames can be dropped.
- Dropped frames are measurable.
- Processing cannot accumulate unlimited latency.

### Metrics

- Source FPS is available where possible.
- Received FPS is measurable.
- Processed FPS is measurable.
- Dropped frames are measurable.
- Latency can be measured.

### Testing

- Downloaded CCTV video is successfully processed.
- At least one realistic surveillance-style video is tested.
- Additional video-property testing is performed where practical.
- Webcam is tested if available.
- RTSP is honestly reported as untested if no RTSP source exists.

### Performance

- A 24–30 FPS 720p/1080p test video should ideally sustain approximately real-time processing in the basic pipeline.
- Persistent processing below ~15 FPS should be investigated.
- Persistent latency above ~500 ms should be investigated.
- Queue saturation should be investigated.
- Continuous memory growth should be investigated.

These are engineering warning thresholds, not final production requirements.

### Scope discipline

- No fake AI output.
- No fake alerts.
- No fake ANPR.
- No fake detections.
- No production dashboard.
- No unnecessary optimization infrastructure.

---

# 49. Definition of Done

The milestone is complete when:

1. A real downloaded surveillance/video file can be ingested.
2. Frames are converted into the IBVAP Frame representation.
3. Frame metadata is available.
4. Source identity is preserved.
5. Frame numbering works.
6. Timestamp handling works.
7. FPS metrics work.
8. Processing latency can be observed.
9. A bounded buffer exists.
10. The initial buffer capacity is 3 frames.
11. Buffer capacity is configurable.
12. Frame dropping behavior is defined and measurable.
13. Capture and processing are decoupled.
14. The selected concurrency model is documented and justified.
15. Source errors are handled.
16. End-of-stream is handled.
17. Shutdown is clean.
18. The architecture supports future webcam sources.
19. The architecture supports future RTSP sources.
20. The architecture supports multiple cameras conceptually.
21. The future object detector has a clean integration point.
22. No AI functionality is falsely simulated.
23. At least one realistic downloaded CCTV/surveillance video is validated.
24. Performance baseline numbers are recorded.
25. Limitations are documented honestly.
26. The implementation has not unnecessarily expanded into Milestone 3.

---

# 50. Required Final Report From Antigravity

After implementation, STOP and provide a detailed report containing:

## 1. Milestone summary

What was implemented?

## 2. Milestone 1 architecture reused

What was reused and what was changed?

## 3. Files/modules changed

Explain important files and their responsibilities.

## 4. Video source abstraction

Explain how FILE, WEBCAM, and RTSP are represented.

## 5. Frame lifecycle

Explain:

Source
→ Capture
→ Buffer
→ Processing
→ Metrics

## 6. Concurrency model

Explicitly report:

- selected approach
- why it was selected
- alternatives considered
- limitations
- future migration path

## 7. Buffering strategy

Report:

- default capacity
- configurable capacity
- overflow policy
- stale-frame handling
- why the strategy was selected

## 8. Error handling

Explain:

- open failures
- decode failures
- EOF
- disconnection design
- shutdown

## 9. Performance metrics

Report actual results:

- video resolution
- source FPS
- received FPS
- processed FPS
- dropped frames
- average latency
- maximum latency
- CPU usage if available
- memory usage if available

## 10. Real-time vs maximum-throughput benchmark

Clearly distinguish:

- real-time simulation result
- maximum-throughput result

Do not confuse these measurements.

## 11. Testing

List every test performed and its result.

## 12. RTSP status

Explicitly state one:

- RTSP tested successfully
- RTSP tested using a local simulated RTSP source
- RTSP architecture prepared but validation deferred because no source was available

Never claim a test that was not actually performed.

## 13. Limitations

Be explicit about anything not tested.

## 14. Problems encountered

Report errors, workarounds, or architectural changes.

## 15. Future decoder/optimization path

Explain whether OpenCV is sufficient for the current stage and when FFmpeg/GStreamer/DeepStream might become necessary.

## 16. Future AI integration

Explain exactly where Milestone 3 object detection will connect.

## 17. Next milestone

Explain what should happen in Milestone 3.

Then STOP.

Do not automatically implement Milestone 3.

---

# 51. Future Roadmap Context

The planned IBVAP development sequence is:

### Milestone 1
Foundation & architecture — COMPLETED

### Milestone 2
Video ingestion & frame pipeline — CURRENT

### Milestone 3
Person and vehicle object detection

### Milestone 4
Multi-object tracking

### Milestone 5
Spatial intelligence / zones / virtual fences / line crossing

### Milestone 6
Event engine

### Milestone 7
Loitering and temporal behavior

### Milestone 8
ANPR

### Milestone 9
Face detection

### Milestone 10
Night-time analytics

### Milestone 11
Suspicious-activity intelligence

### Milestone 12
Risk engine

### Milestone 13
Evidence management

### Milestone 14
Backend and persistence

### Milestone 15
Real-time command dashboard

### Milestone 16
Camera and rule configuration

### Milestone 17
Multi-camera intelligence

### Milestone 18
Performance optimization

### Milestone 19
Deployment

### Milestone 20
Full validation and SIH demonstration

Do not skip milestones merely to make the project appear complete.

---

# 52. Engineering Principles

These principles apply throughout IBVAP development.

1. Correctness before optimization.
2. Real measurements before performance claims.
3. Low latency is more important than processing stale frames.
4. One camera failure must not take down the whole system.
5. AI must remain modular and replaceable.
6. Do not fake functionality.
7. Do not add infrastructure without a real requirement.
8. Keep source-specific logic inside source adapters.
9. Keep AI-specific logic inside perception modules.
10. Keep surveillance/business rules outside AI models.
11. Preserve camera identity throughout the pipeline.
12. Every future milestone must be independently testable.
13. Use downloaded real-world surveillance footage aggressively during development.
14. Do not treat the absence of physical CCTV hardware as a blocker for AI development.
15. Use controlled local simulation when live infrastructure is unavailable.
16. Optimize only after measuring the actual bottleneck.

---

# 53. Final Instruction

Implement **Milestone 2 only**.

Start by inspecting the completed Milestone 1 implementation.

Build the video ingestion and frame-processing infrastructure described in this document.

Use real downloaded CCTV/surveillance video as the mandatory validation source.

Use a webcam for live validation if available.

Prepare RTSP support architecturally, but do not falsely claim RTSP validation without an actual test source.

Use an initial bounded buffer capacity of 3 frames and make it configurable.

Select and justify an appropriate concurrency model.

Use OpenCV as the initial decoder/capture technology unless a concrete technical issue in the existing environment requires another choice.

Establish real performance measurements and report them.

Do not implement future AI capabilities.

Do not create fake detections or fake surveillance events.

Do not automatically continue to Milestone 3.

When Milestone 2 passes its acceptance criteria, provide the required final report and stop.
