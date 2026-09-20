# IBVAP — Milestone 1
## First Implementation Instruction: Project Foundation & Architecture

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Development agent:** Google Antigravity  
**Milestone:** 1 — Foundation, Architecture, Contracts, and Development Standards  
**Status:** Initial implementation  
**Important:** Do NOT implement AI inference, detection, tracking, ANPR, face recognition, suspicious-activity models, or production dashboard functionality in this milestone.

---

# 1. Project Context

We are building **IBVAP (Intelligent Border Video Analytics Platform)** for SIH26187.

The goal is to transform existing standard IP-based CCTV infrastructure into an intelligent software-defined surveillance platform.

The final system should be able to ingest live CCTV streams and perform AI-powered video analytics without requiring dedicated proprietary FRS, ANPR, or smart-camera hardware.

The final platform is expected to support:

- Human detection and tracking
- Vehicle detection and classification
- Face detection
- Automatic Number Plate Recognition (ANPR)
- Virtual-fence intrusion detection
- Suspicious-activity detection
- Night-time movement detection
- Real-time alerts
- Event logging
- Evidence capture
- Multi-camera monitoring
- Integration with command-and-control systems
- Scalable deployment across remote/strategic locations

The final product should be treated as a **security operations / surveillance intelligence platform**, not simply a YOLO demo.

The fundamental processing philosophy is:

**Detect → Track → Understand → Decide → Alert → Record Evidence**

---

# 2. The Most Important Rule for This Milestone

Do not attempt to build the complete IBVAP system now.

This milestone exists to create a strong foundation that future milestones can build on.

Do NOT implement:

- YOLO inference
- Object detection
- Object tracking
- Face detection
- Face recognition
- License-plate detection
- OCR
- Suspicious-activity AI
- Night enhancement AI
- Risk scoring logic
- Real CCTV/RTSP integration
- Full production dashboard
- Fake detections
- Fake alerts
- Fake camera feeds
- Hard-coded sample results pretending to be real AI output

If something is not implemented yet, represent it as an explicit future capability rather than simulating it.

The purpose of Milestone 1 is architecture and engineering discipline.

---

# 3. First Action: Inspect the Existing Workspace

Before creating or modifying anything:

1. Inspect the entire existing workspace.
2. Identify existing source code.
3. Identify existing configuration files.
4. Identify existing frontend/backend projects.
5. Identify existing Python environments or package manifests.
6. Identify existing documentation.
7. Identify any reusable components.
8. Determine whether this is an empty project or an existing partially implemented project.
9. Do not overwrite or delete existing work without understanding it.
10. Reuse useful existing components only when they fit the architecture.

Create a short internal assessment before making major structural changes.

If the workspace already contains a project, preserve useful work and adapt it rather than blindly replacing it.

---

# 4. Architectural Objective

The final IBVAP system must be modular.

The architecture should allow us to replace one AI technology without rewriting the entire application.

For example:

- YOLO should be replaceable by another detector.
- ByteTrack could later be replaced by BoT-SORT or another tracker.
- PaddleOCR could later be replaced by another OCR engine.
- A face detector should be replaceable independently.
- The backend should not contain model-specific inference logic.
- The frontend should not directly depend on AI model internals.
- Event rules should not depend directly on a particular neural-network framework.

Use stable internal interfaces/contracts between modules.

The conceptual architecture is:

CCTV / Video Sources
↓
Video Ingestion
↓
Frame Processing
↓
AI Perception
↓
Object Tracking
↓
Spatial Intelligence
↓
Event Engine
↓
Risk Engine
↓
Evidence / Alert Management
↓
Persistence
↓
API / WebSocket
↓
Command Dashboard

This is the target architecture. Only the foundation is being created now.

---

# 5. Core Architectural Layers

Design the project around these conceptual layers.

## Layer 1 — Video Ingestion

Responsible for obtaining video frames from sources.

Future sources:

- Local video files
- Webcam
- RTSP IP cameras
- Potentially other streaming protocols

This layer should not know how AI inference works.

---

## Layer 2 — Frame Processing

Responsible for:

- Frame representation
- Frame metadata
- Timestamp handling
- Resolution information
- Basic preprocessing hooks
- Frame lifecycle management

It should provide clean input to future inference modules.

---

## Layer 3 — AI Perception

Future responsibility:

- Person detection
- Vehicle detection
- Vehicle classification
- Face detection
- Plate detection
- Other object detection

This layer should expose standardized detection outputs.

Do not implement the models yet.

---

## Layer 4 — Tracking

Future responsibility:

- Maintain object identities across frames
- Generate track IDs
- Maintain trajectories
- Maintain object history
- Track confidence/state

Tracking should consume generic detections rather than depend on a specific detector.

---

## Layer 5 — Spatial Intelligence

Future responsibility:

- Polygon zones
- Restricted areas
- Virtual fences
- Virtual lines
- Entry/exit detection
- Direction detection
- Region-of-interest logic

Spatial rules should operate on generic tracks.

---

## Layer 6 — Event Engine

Future responsibility:

Convert observations into security events.

Examples:

- Restricted-zone intrusion
- Virtual-line crossing
- Loitering
- Wrong-direction movement
- Night movement
- Vehicle intrusion
- ANPR event
- Face-detection event
- Compound/correlated event

The event engine should not run neural networks itself.

It should consume structured information produced by perception, tracking, and spatial intelligence.

---

## Layer 7 — Risk Engine

Future responsibility:

Assign severity/risk to events.

Example conceptual factors:

- Event type
- Location
- Time of day
- Object type
- Duration
- Repeated violations
- Combination with other events

Potential severity levels:

- LOW
- MEDIUM
- HIGH
- CRITICAL

The exact scoring system will be designed in a later milestone.

---

## Layer 8 — Evidence Management

Future responsibility:

Associate security events with evidence such as:

- Snapshot
- Short video clip
- Timestamp
- Camera
- Object/track information
- Detection metadata

The platform should prioritize relevant event evidence rather than unnecessarily storing every frame forever.

---

## Layer 9 — Persistence

Future responsibility:

Store:

- Cameras
- Camera configurations
- Zones
- Virtual lines
- Events
- Alerts
- Evidence metadata
- Track/event metadata
- System configuration

The exact production database design will be finalized later.

---

## Layer 10 — API / Real-Time Communication

Future responsibility:

REST APIs for:

- Camera management
- Configuration
- Event history
- Alert management
- System status
- Analytics

WebSocket or equivalent real-time communication for:

- New alerts
- Live event updates
- Camera state changes
- Real-time dashboard notifications

---

## Layer 11 — Frontend

Future responsibility:

Security operator dashboard containing:

- Camera grid
- Live monitoring
- Active alerts
- Event history
- Event details
- ANPR events
- Camera configuration
- Zone configuration
- System health

Do not build the full dashboard in Milestone 1.

---

# 6. Core Domain Concepts

Establish clear internal concepts/contracts for at least the following.

## Camera

Represents a physical or logical CCTV source.

Conceptual information:

- Camera ID
- Name
- Location
- Stream source/configuration
- Status
- Capabilities
- Configuration
- Associated zones
- Associated virtual lines

---

## VideoStream

Represents the active stream associated with a camera.

Future information may include:

- Stream state
- Source type
- Connection status
- Resolution
- FPS
- Last received frame
- Error state

---

## Frame

Represents one processed video frame.

Conceptual metadata:

- Frame ID
- Camera ID
- Timestamp
- Frame index
- Width
- Height
- Source information

The architecture must support future real-time processing.

---

## Detection

Represents an AI perception result.

Conceptual information:

- Detection ID
- Camera ID
- Frame ID
- Object class
- Bounding box
- Confidence
- Timestamp
- Optional model/source metadata

A Detection should represent what an AI model sees, not what the security system concludes.

---

## Track

Represents the temporal identity of an object.

Conceptual information:

- Track ID
- Camera ID
- Object class
- Current position
- Bounding box
- Trajectory/history
- First seen timestamp
- Last seen timestamp
- Tracking state

A Track should be independent of the specific detector used.

---

## Zone

Represents an area configured by an operator.

Potential types:

- Normal zone
- Restricted zone
- Monitoring zone
- Entry zone
- Exit zone

A zone should support geometry/configuration independently of the AI model.

---

## VirtualLine

Represents a line used to detect crossing/direction events.

Potential configuration:

- Line ID
- Camera ID
- Geometry
- Allowed direction
- Event configuration

---

## Event

Represents something meaningful detected by the surveillance system.

Examples:

- Intrusion
- Loitering
- Line crossing
- Night movement
- Vehicle entry
- ANPR detection

Conceptual information:

- Event ID
- Event type
- Camera
- Track/object
- Timestamp
- Location
- Confidence/reliability
- Severity
- Status
- Evidence references

---

## RiskAssessment

Represents the security significance of an event.

Potential information:

- Risk score
- Severity
- Contributing factors
- Explanation
- Rule/version used

The architecture should allow the future system to explain why a risk level was assigned.

---

## Alert

Represents an event that requires operator attention.

Potential information:

- Alert ID
- Event ID
- Severity
- State
- Created time
- Acknowledgement time
- Resolution time
- Operator information
- Escalation information

Potential lifecycle:

DETECTED → ACTIVE → ACKNOWLEDGED → INVESTIGATING → RESOLVED

---

## Evidence

Represents supporting material associated with an event.

Potential information:

- Evidence ID
- Event ID
- Type
- File/reference
- Timestamp
- Camera
- Retention metadata

Potential types:

- Snapshot
- Video clip
- Metadata

---

## SystemConfiguration

Represents global configuration.

Potential areas:

- Camera defaults
- Event thresholds
- Logging
- Storage
- Processing
- Alerting
- Runtime settings

Configuration must be separated from source code wherever practical.

---

# 7. Data Flow Contract

The architecture should enforce the following conceptual data flow:

Video Source
→ VideoStream
→ Frame
→ Detection
→ Track
→ Spatial Observation
→ Event
→ RiskAssessment
→ Alert
→ Evidence
→ Persistence
→ API/WebSocket
→ Dashboard

Do not create direct dependencies that bypass these conceptual boundaries without a strong architectural reason.

For example:

Bad:

Dashboard → YOLO directly

Better:

Dashboard → API → Event/Monitoring Service → persisted/system state

Another bad design:

Event Engine → directly call a specific YOLO model

Better:

Perception Layer → standardized Detection → Event/Tracking layers

---

# 8. Replaceable AI Components

The architecture must support future interchangeable implementations.

Potential future perception stack:

## Object detector

Possible technology:

- Ultralytics YOLO ecosystem

Future responsibility:

- Person detection
- Vehicle detection
- Other relevant classes

Do not install or integrate it yet unless required solely for dependency validation.

---

## Tracker

Possible technologies:

- ByteTrack
- BoT-SORT

The tracker should consume generic detections.

---

## Plate detection + OCR

Potential future stack:

Vehicle detection
→ Plate detection
→ Plate crop
→ OCR

Potential OCR technologies:

- PaddleOCR
- EasyOCR
- Tesseract

Do not implement ANPR yet.

---

## Face detection

Potential future candidates:

- RetinaFace
- SCRFD
- MTCNN

Do not implement face detection or recognition yet.

---

## Video infrastructure

Potential technologies:

- OpenCV
- FFmpeg

Future responsibility:

- Video files
- Webcam
- RTSP streams
- Frame decoding

Do not implement real CCTV ingestion yet.

---

## GPU acceleration

The development machine includes an NVIDIA RTX 4060-class laptop GPU.

The architecture should be GPU-ready, but must not hard-code the application to one GPU.

Future optimization options:

- CUDA
- ONNX
- TensorRT
- NVIDIA DeepStream

Do not introduce DeepStream or TensorRT in Milestone 1.

Optimization comes after a correct working pipeline exists.

---

# 9. Error Isolation Requirement

This is a security surveillance platform.

A failure in one camera must not bring down the entire platform.

Design future processing so that:

Camera A failure
≠
Camera B failure

Similarly:

AI inference failure
≠
entire backend failure

OCR failure
≠
vehicle detection failure

One event processing failure
≠
all camera processing stopping

Prepare the architecture for isolated error handling and structured logging.

---

# 10. Real-Time Requirement

The final system will process continuous streams.

Do not design the entire application around:

request → process one image → return response

Instead prepare the architecture for:

continuous stream
→ frame processing
→ asynchronous inference
→ tracking
→ events
→ real-time notifications

The final platform must support multiple cameras.

Do not assume a single global video stream.

---

# 11. Multi-Camera Requirement

The architecture must be camera-aware from day one.

Every important piece of runtime information should be traceable to its source camera.

For example:

Detection → Camera ID

Track → Camera ID

Event → Camera ID

Evidence → Camera ID

This will allow future expansion to:

Camera 1
Camera 2
Camera 3
...
Camera N

Do not attempt cross-camera person re-identification in Milestone 1.

That is a future advanced feature.

---

# 12. Configuration-Driven Design

Avoid hard-coding surveillance rules.

Future examples:

Instead of hard-coding:

"Loitering = 60 seconds"

we should eventually configure:

loitering_threshold = configurable

Instead of hard-coding:

"Zone X is restricted"

the operator should eventually configure the zone.

Instead of hard-coding:

"Night = 8 PM to 6 AM"

the system should eventually support configurable operating hours.

Milestone 1 should establish the architecture needed for configuration-driven behavior.

---

# 13. Logging Requirements

Create a structured logging strategy.

Logs should eventually distinguish:

- INFO
- WARNING
- ERROR
- DEBUG

Future logs should make it possible to understand:

- Camera connection failures
- Frame processing failures
- Model failures
- OCR failures
- Event engine failures
- Database failures
- API failures

Do not log sensitive data unnecessarily.

Do not print random debugging statements throughout the project.

---

# 14. Security and Privacy Principles

Even though this is a prototype, architecture should respect security principles.

Important considerations:

- Do not expose camera credentials in source code.
- Do not commit secrets.
- Use environment/configuration mechanisms for credentials.
- Avoid unnecessary storage of face imagery.
- Treat surveillance evidence as sensitive.
- Keep authentication/authorization extensible for later implementation.
- Avoid exposing internal model endpoints directly to the frontend.
- Validate API inputs.
- Plan for audit logging.
- Keep evidence access controlled in future versions.

The final production system will require a stronger security review.

---

# 15. Hardware-Agnostic Requirement

The central value proposition of IBVAP is that it can work with existing CCTV infrastructure.

Do not architect the system around a proprietary smart camera.

The AI should primarily exist in the software pipeline.

Potential future architecture:

Existing IP Camera
→ RTSP
→ IBVAP
→ AI inference
→ Intelligence
→ Alert

The platform should not require a special camera for basic intelligence.

---

# 16. Deployment Philosophy

The final system should be deployable in environments where internet connectivity may be limited or unreliable.

Therefore, future architecture should support:

- Local inference
- Local event processing
- Local evidence storage
- Local dashboard access
- Optional synchronization with central systems

Do not assume permanent cloud connectivity.

Cloud integration may be added later.

---

# 17. Future Deployment Architecture

The long-term deployment may look like:

Border Camera
→ Local/Edge IBVAP Node
→ Local AI inference
→ Local events
→ Local operator dashboard

Optional:

Local Node
→ Central Command Center
→ Aggregated events
→ Cross-site monitoring

The architecture should not prevent this future model.

---

# 18. Suggested Technology Direction

Do not blindly install every technology below.

This is the current target stack to evaluate during future milestones.

### Backend / AI

- Python
- FastAPI
- PyTorch
- OpenCV
- FFmpeg

### Detection

- Ultralytics YOLO ecosystem

### Tracking

- ByteTrack / BoT-SORT

### OCR

- PaddleOCR initially considered

### Face

- RetinaFace / SCRFD candidates

### Database

- PostgreSQL

### Real-time

- WebSockets

### Frontend

- React

### Deployment

- Docker

### Optimization

- ONNX
- TensorRT
- NVIDIA DeepStream

The exact final stack must be validated experimentally.

Do not add technologies simply because they are popular.

---

# 19. What We Build in Milestone 1

Implement only the following:

## A. Repository/project organization

Create a clean modular project structure.

## B. Backend foundation

Prepare the backend/application boundary.

## C. Domain model foundation

Define the concepts/contracts for:

- Camera
- VideoStream
- Frame
- Detection
- Track
- Zone
- VirtualLine
- Event
- RiskAssessment
- Alert
- Evidence
- SystemConfiguration

## D. Configuration foundation

Prepare configuration handling.

## E. Logging foundation

Prepare structured application logging.

## F. Error-handling foundation

Prepare centralized/consistent error handling where appropriate.

## G. API foundation

Prepare the API boundary without implementing the complete functionality.

## H. Real-time communication boundary

Prepare the architecture for future WebSocket/event communication.

## I. Frontend foundation

Only establish the frontend project boundary and a minimal structural shell if needed.

Do not create a fake finished dashboard.

## J. Documentation

Document:

- Architecture
- Data flow
- Module responsibilities
- Future AI integration points
- Development rules
- Current limitations
- Next milestone

---

# 20. What Must NOT Be Added Just for Appearance

Do not create fake:

- CCTV feeds
- detections
- bounding boxes
- alerts
- ANPR results
- face matches
- risk scores
- tracking IDs

A placeholder UI is acceptable only if it is explicitly labeled as placeholder/unimplemented.

We care more about architectural correctness than visual impressiveness at this stage.

---

# 21. Future Development Roadmap

The following is the intended roadmap.

## Milestone 1
Foundation and architecture.

CURRENT MILESTONE.

---

## Milestone 2 — Video Ingestion

Build:

Video file
→ Frame extraction
→ Frame representation
→ Processing pipeline

Then:

Webcam
→ Frame pipeline

Then:

RTSP
→ Frame pipeline

Validation:

- stable frame acquisition
- FPS measurement
- timestamp correctness
- reconnect behavior
- camera isolation

---

## Milestone 3 — Object Detection

Integrate a real pretrained detector.

Initial targets:

- Person
- Car
- Motorcycle
- Bus
- Truck
- Other useful vehicle classes

Output:

Detection objects with:

- bounding box
- class
- confidence
- camera
- timestamp

Measure:

- FPS
- latency
- precision/recall on relevant validation data
- GPU utilization

---

## Milestone 4 — Multi-Object Tracking

Integrate a tracker.

Goals:

- persistent IDs
- trajectories
- object history
- entry/exit times
- track lifecycle

Test:

- multiple people
- occlusion
- vehicles
- crowded scenes

---

## Milestone 5 — Spatial Intelligence

Implement:

- Polygon zones
- Restricted zones
- Virtual fences
- Virtual lines
- Line crossing
- Direction
- Region-based rules

This will be one of the major application-specific components.

---

## Milestone 6 — Event Engine

Implement:

- Intrusion
- Line crossing
- Zone entry
- Vehicle intrusion
- Basic movement events

Events must be generated from real tracks and scene state.

No fake event generation.

---

## Milestone 7 — Loitering and Temporal Behavior

Implement temporal reasoning.

Example:

Person enters zone
→ timer starts
→ remains beyond threshold
→ loitering event

This milestone establishes temporal behavior analysis.

---

## Milestone 8 — ANPR

Pipeline:

Vehicle detection
→ Plate localization
→ Plate crop
→ OCR
→ Validation/normalization
→ ANPR event
→ Evidence

Evaluate Indian plate scenarios where possible.

ANPR must handle imperfect OCR rather than blindly trusting one OCR result.

---

## Milestone 9 — Face Detection

Implement face detection.

Keep face detection separate from identity recognition.

If identity recognition is eventually required, it should be implemented as a separate controlled module with appropriate privacy/security considerations.

---

## Milestone 10 — Night-Time Analytics

Investigate:

- low-light preprocessing
- enhancement
- infrared footage
- detection performance at night
- movement detection

Do not assume enhancement is automatically beneficial.

Benchmark before and after.

---

## Milestone 11 — Suspicious Activity Intelligence

Start with explainable rules.

Examples:

- repeated zone entry
- unusual direction
- prolonged presence
- night + restricted zone
- repeated movement
- unusual object behavior

Only after rule-based intelligence works should we consider ML anomaly detection.

---

## Milestone 12 — Risk Engine

Combine event factors into:

- score
- severity
- explanation

Example:

Night + restricted-zone intrusion + long duration
→ higher severity

The exact scoring system should be validated experimentally.

---

## Milestone 13 — Evidence Management

For significant events:

- snapshot
- event metadata
- optional short clip
- timestamp
- camera
- track ID

Implement retention/storage strategy.

---

## Milestone 14 — Backend and Persistence

Complete:

- camera APIs
- event APIs
- alert APIs
- evidence APIs
- configuration APIs
- PostgreSQL integration
- authentication/authorization foundation

---

## Milestone 15 — Real-Time Dashboard

Build the operator interface.

Core views:

- Live cameras
- Alerts
- Event history
- Camera status
- Event details
- ANPR
- Configuration

Real-time events should appear without manual page refresh.

---

## Milestone 16 — Camera/Zone Configuration

Allow operators to configure:

- cameras
- zones
- virtual lines
- directions
- thresholds
- alert rules

---

## Milestone 17 — Multi-Camera Intelligence

Expand from one camera to multiple cameras.

First goal:

Independent parallel camera processing.

Later:

Cross-camera analytics.

Cross-camera person re-identification is an advanced feature and must not become a dependency for the basic system.

---

## Milestone 18 — Performance Optimization

Investigate:

- ONNX
- TensorRT
- batching
- GPU utilization
- frame skipping
- inference scheduling
- NVIDIA DeepStream

Only optimize after measuring bottlenecks.

---

## Milestone 19 — Deployment

Prepare:

- Docker
- configuration management
- local deployment
- edge deployment
- monitoring
- health checks
- recovery

---

## Milestone 20 — Final Validation

Create realistic scenarios:

1. Normal person movement
2. Restricted-zone entry
3. Virtual-line crossing
4. Loitering
5. Vehicle entry
6. ANPR
7. Night movement
8. Multiple simultaneous cameras
9. Camera failure
10. AI model failure
11. Network interruption
12. High-load scenario

Measure:

- Detection accuracy
- Tracking performance
- Event accuracy
- Alert latency
- FPS
- Resource usage
- False positives
- False negatives
- Recovery behavior

---

# 22. Future Advanced Features

These are possibilities, not current requirements.

Potential later features:

- Cross-camera tracking
- Person re-identification
- Vehicle re-identification
- Heatmaps
- Historical trajectory visualization
- Advanced anomaly detection
- Temporal action recognition
- Audio/event fusion if relevant
- Central command integration
- Offline-first edge deployment
- Model management
- Camera health monitoring
- Alert escalation
- Operator audit logs
- Role-based access control
- Multi-site deployment

Do not implement these now.

---

# 23. Definition of Done for Milestone 1

Milestone 1 is complete only when:

- The existing workspace has been inspected.
- The project has a clean modular architecture.
- The major module boundaries are clear.
- Core domain concepts/contracts exist.
- Configuration has a clear foundation.
- Logging has a clear foundation.
- Error handling has a clear foundation.
- Backend/frontend boundaries are clear.
- Real-time communication has a defined boundary.
- AI modules are replaceable by design.
- Multi-camera processing is supported architecturally.
- No fake AI functionality has been introduced.
- No unnecessary heavy dependencies have been added.
- Documentation explains the architecture.
- The project can be started/validated according to its foundation setup.
- The implementation clearly identifies what belongs to Milestone 2.
- No automatic progression into Milestone 2 occurs.

---

# 24. Required Final Report from Antigravity

When Milestone 1 is complete, stop and report back.

The report must contain:

## 1. Workspace assessment

What already existed?

## 2. Architecture

Explain every major module.

## 3. Folder/project structure

Explain the purpose of important directories/files.

## 4. Domain contracts

Explain:

Camera → Stream → Frame → Detection → Track → Zone/Line → Event → Risk → Alert → Evidence

## 5. Dependency decisions

List dependencies added and explain why each one is needed now.

## 6. Deferred technologies

Explain which technologies were intentionally not added yet and why.

## 7. Data flow

Explain the intended runtime data flow.

## 8. Failure isolation

Explain how the architecture will prevent one camera/module failure from taking down the system.

## 9. Future AI integration

Explain where YOLO, tracking, OCR, face detection, and future models will connect.

## 10. Testing performed

List all validation/tests performed for the foundation.

## 11. Known limitations

Be honest about what is not implemented.

## 12. Recommended next milestone

Explain exactly what must happen in Milestone 2.

Then STOP.

Do not automatically implement Milestone 2.

---

# 25. Engineering Rules for the Entire Project

These rules apply to every future milestone.

### Rule 1 — No fake AI

Never simulate AI output and present it as real.

### Rule 2 — Modular AI

AI models must be replaceable.

### Rule 3 — Measure before optimizing

Do not add TensorRT/DeepStream/etc. without identifying a real bottleneck.

### Rule 4 — One milestone at a time

Do not implement future milestones without explicit instruction.

### Rule 5 — Test every milestone

A milestone is not complete because the code runs once.

### Rule 6 — Keep security in mind

No secrets in source code.

### Rule 7 — Camera isolation

One camera failure must not crash all cameras.

### Rule 8 — Explainable alerts

Whenever possible, an alert should have a clear reason.

### Rule 9 — Evidence-backed events

Important events should eventually have supporting evidence.

### Rule 10 — Don't over-engineer

Avoid unnecessary microservices, message brokers, Kubernetes, or complex infrastructure unless actual scale/performance requirements justify them.

### Rule 11 — Prefer proven components

Use mature open-source libraries/models when they solve the problem adequately.

### Rule 12 — Build our intelligence where it matters

Our original contribution should increasingly be in:

- spatial reasoning
- event correlation
- surveillance rules
- risk assessment
- evidence management
- operator workflow
- system integration
- deployment architecture

rather than reinventing standard object detection/OCR technology.

---

# 26. Final Vision

The finished IBVAP should eventually behave like this:

A CCTV camera observes a scene.

The platform receives the stream.

AI detects:

**Person #21**

The tracker follows the person.

The spatial engine determines:

**Person #21 entered Restricted Zone A.**

The temporal engine determines:

**The person has remained there for 43 seconds.**

The context engine determines:

**Current time is nighttime.**

The event engine creates:

**Restricted-zone intrusion + prolonged presence + night movement.**

The risk engine evaluates:

**HIGH / CRITICAL**

The evidence manager captures:

- timestamp
- camera
- frame
- event metadata
- optional short video clip

The backend stores the event.

The WebSocket layer pushes it to the operator.

The dashboard displays:

**CRITICAL ALERT — CAM-03 — Restricted Zone Intrusion**

The operator acknowledges it.

The incident becomes part of the audit/event history.

That complete chain is what we are ultimately building.

---

# 27. Current Instruction

Start **Milestone 1 only**.

First inspect the workspace.

Then establish the foundation and architecture described above.

Do not implement future AI capabilities.

Do not create fake functionality.

Do not proceed to Milestone 2 automatically.

After completing Milestone 1, provide the required final report and stop.
