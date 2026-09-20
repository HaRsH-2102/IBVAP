# IBVAP — Milestone 6 Specification (Revised)

**Project:** SIH26187 — Intelligent Border Video Analytics Platform (IBVAP)  
**Milestone:** M6 — Event Interpretation & Real-Time Alert Generation  
**Status:** 🟡 SPECIFICATION — NOT STARTED  
**Prerequisites:** M1–M5 completed and frozen

---

# 1. Milestone Purpose

Milestone 5 produces spatial facts:

```text
ZONE_ENTER
ZONE_EXIT
LINE_CROSS
```

These are geometric events.

M6 introduces the layer that answers:

> **What does this spatial event mean from a configured security-policy perspective?**

M6 transforms low-level `SpatialEvent[]` into higher-level `SecurityEvent[]` and manages actionable `Alert` state.

The architectural boundary is:

```text
M5
SpatialEvent[]
      ↓
M6 Event Interpretation
      ↓
SecurityEvent[]
      ↓
Alert Manager
      ↓
SQLite Persistence + Event Log
```

M6 must not modify M5.

---

# 2. Core Objective

Build a modular event interpretation engine capable of:

- consuming spatial events
- validating and normalizing them
- evaluating configurable security rules
- assigning severity
- creating security events
- performing basic event correlation
- generating alerts
- preventing duplicate processing/alert storms
- maintaining alert lifecycle state
- persisting events and alerts across process restarts
- logging events for auditability
- preserving traceability back to M5
- operating in real time
- remaining independent of YOLO, ByteTrack, and OpenCV

---

# 3. What M6 Must NOT Implement

Do NOT implement:

- ANPR
- OCR
- facial recognition
- face embeddings
- suspicious-activity ML models
- advanced behavior recognition
- night-time detection
- cross-camera re-identification
- LLM-based reasoning
- command-center frontend
- SMS/email/WhatsApp notifications
- external emergency integrations
- autonomous response
- weapon detection
- threat-classification models
- new object detectors
- new trackers
- changes to M1–M5

M6 is primarily a **rule-based event interpretation, basic correlation, alert lifecycle, and persistence layer**.

Advanced behavioral reasoning belongs to M7+.

---

# 4. Frozen Upstream Boundary

M6 receives the canonical M5 output:

```text
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
 ↓
M6
```

M6 must not reach backward into:

- YOLO model outputs
- PyTorch tensors
- OpenCV frames
- ByteTrack internals
- raw detector outputs

unless a future milestone explicitly defines a new interface.

---

# 5. High-Level Architecture

```text
                    M5
                     │
                     ▼
              SpatialEvent[]
                     │
                     ▼
          ┌─────────────────────┐
          │ Event Normalizer    │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ Rule Evaluation     │
          │ Engine              │
          └──────────┬──────────┘
                     │
             ┌───────┴────────┐
             ▼                ▼
      SecurityEvent[]    Basic Correlator
             │                │
             └───────┬────────┘
                     ▼
          ┌─────────────────────┐
          │ Alert Manager       │
          └──────────┬──────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
          SQLite Store   Event Log
              │
              ▼
        Active Alert State
```

The exact module names may differ, but these responsibilities must remain separated.

---

# 6. M6 Components

M6 should contain conceptual modules for:

## 6.1 Event Normalizer

Validates and normalizes incoming M5 events.

## 6.2 Rule Engine

Evaluates configured security rules.

## 6.3 Security Event Builder

Converts matched rules into canonical security events.

## 6.4 Basic Correlator

Groups related events within a small configurable temporal/context window.

## 6.5 Alert Manager

Creates, deduplicates, updates, and resolves alerts.

## 6.6 Persistence Layer

Stores security events and alert state in SQLite.

## 6.7 Event/Alert Repository

Provides a clean abstraction between business logic and SQLite.

---

# 7. Security Event vs Alert

This distinction is mandatory.

### Security Event

An interpreted security-relevant fact.

Example:

```text
Track 17
entered restricted zone
```

### Alert

An actionable state generated from one or more security events.

Example:

```text
HIGH PRIORITY ALERT
Restricted-zone intrusion detected
Camera: BOP_CAM_04
Track: 17
```

One alert may eventually contain multiple correlated security events.

---

# 8. Initial Security Event Types

Keep the initial vocabulary small:

```text
ZONE_INTRUSION
RESTRICTED_ZONE_ENTRY
RESTRICTED_ZONE_EXIT
BORDER_LINE_CROSSING
VEHICLE_ZONE_INTRUSION
```

Do not create speculative event types.

The architecture must allow future additions.

---

# 9. Severity Model

Initial severity levels:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

Severity is configuration-driven.

Example policies:

```text
ordinary zone entry → LOW
restricted zone entry → HIGH
restricted border crossing → CRITICAL
```

These are demonstration policies, not claims about real operational threat levels.

Severity means **configured importance**, not certainty that a real-world threat exists.

---

# 10. Rule Contract

Conceptually:

```text
Rule
├── rule_id
├── name
├── enabled
├── priority
├── event_type
├── camera_scope
├── spatial_object_scope
├── object_class_scope
├── direction_scope
├── severity
├── security_event_type
├── alert_policy
└── correlation_policy
```

Unspecified constraints mean "don't care."

---

# 11. Rule Matching

Rules may match:

### Event type

```text
ZONE_ENTER
ZONE_EXIT
LINE_CROSS
```

### Camera

```text
camera_01
camera_02
ALL
```

### Spatial object

```text
zone_01
line_01
ALL
```

### Object class

Future-compatible:

```text
person
car
motorcycle
bus
truck
UNKNOWN
ALL
```

### Direction

```text
A_TO_B
B_TO_A
BOTH
```

A rule matches only when all configured constraints are satisfied.

---

# 12. Object-Class Availability

M5 may not currently provide complete object-class information in every `SpatialEvent`.

Do NOT modify M5 to solve this.

M6 must explicitly support:

```text
object_class = UNKNOWN
```

If a rule requires `person`, `car`, etc. and the class is unknown, that rule must **not falsely match**.

The M6 completion report must document exactly which object-class information is currently available at the M5→M6 boundary.

Future milestones may enrich event context.

---

# 13. Multiple Matching Rules — Intentional Behavior

Multiple enabled rules may legitimately match the same `SpatialEvent`.

Example:

```text
SpatialEvent:
ZONE_ENTER zone_01

Rule A:
any zone entry → LOW

Rule B:
zone_01 entry → HIGH
```

Both rules may produce separate `SecurityEvent`s because they represent different configured policies.

Therefore:

```text
one SpatialEvent
      ↓
Rule A → SecurityEvent A
Rule B → SecurityEvent B
```

This is **intentional**, not a deduplication bug.

The deduplication system must prevent repeated processing of the same:

```text
source_event + rule
```

It must NOT suppress legitimate different rules merely because they originated from the same physical event.

If the operator wants only one policy to win, that must be explicitly represented through rule priority/exclusivity configuration.

---

# 14. Rule Evaluation Order

Rules are evaluated deterministically:

```text
rule priority
→ rule_id
```

Do not depend on dictionary/set ordering or thread scheduling.

Unless an explicit exclusive policy exists, every matching enabled rule may generate its own security event.

---

# 15. Event Normalization

Pipeline:

```text
SpatialEvent
      ↓
validate
      ↓
normalize
      ↓
NormalizedSpatialEvent
```

Validation checks:

- event ID
- camera ID
- timestamp
- track ID where required
- spatial object ID
- event type
- metadata structure

Malformed events must be rejected safely and logged.

Later valid events must continue processing.

---

# 16. Security Event Identity

A security event must preserve a deterministic relationship to:

```text
source_spatial_event_id
+
rule_id
```

This pair is the logical identity basis for duplicate processing prevention.

An external UUID may still be used as the public `event_id`.

---

# 17. Basic Event Correlation — M6 Scope

M6 **will implement basic correlation**, not merely provide an empty extension point.

The purpose is to group closely related security events without performing advanced behavior inference.

Initial correlation window:

```text
5 seconds
```

The value must be configurable.

Initial correlation context should primarily use:

```text
camera_id
+
track_id
```

and optionally relevant spatial/rule context.

Example:

```text
ZONE_ENTER
    +
LINE_CROSS
    +
ZONE_ENTER
```

for the same track/camera within 5 seconds may be associated with one alert context.

M6 must NOT infer:

- intent
- suspicious behavior
- loitering
- threat level from movement patterns
- complex behavioral meaning

Those belong to M7+.

---

# 18. Correlation Rules

Basic correlation must be explicit and deterministic.

Do not use machine learning.

Do not create hidden behavioral heuristics.

A correlation policy should specify:

```text
correlation_policy
├── enabled
├── window_seconds
├── matching_context
└── resulting_alert_policy
```

Default:

```text
enabled = true for demonstration correlation rules
window_seconds = 5
```

If no correlation policy applies, the security event remains independently alertable.

---

# 19. Correlation Boundaries

Initial correlation is:

- same camera
- same track where track context exists
- within configured time window
- explicitly configured event relationships

Do NOT correlate arbitrary events merely because their timestamps are close.

Cross-camera correlation is deferred.

Advanced multi-event behavioral interpretation is deferred to M7+.

---

# 20. Security Event Builder

A `SecurityEvent` should contain:

```text
event_id
event_type
severity
camera_id
track_id
source_spatial_event_id
rule_id
timestamp
status
description
metadata
correlation_id
```

The original M5 event remains traceable.

---

# 21. Alert Deduplication

Initial alert identity should be based on the configured condition:

```text
camera_id
+
track_id
+
rule_id
+
spatial_object_id
```

The implementation must document the exact key.

Important:

Deduplication prevents repeated processing of the same active condition.

It does not suppress legitimately different rule matches.

---

# 22. Alert Lifecycle

Initial states:

```text
OPEN
ACKNOWLEDGED
RESOLVED
```

Expected lifecycle:

```text
OPEN
  ↓
ACKNOWLEDGED
  ↓
RESOLVED
```

The implementation must also support:

```text
OPEN
  ↓
RESOLVED
  ↓
new genuine occurrence
  ↓
new OPEN alert
```

A resolved historical alert must never permanently suppress a later incident.

---

# 23. Alert Persistence Requirement

M6 **must persist security events and alert state across process restarts**.

Pure in-memory alert state is insufficient for the M6 milestone.

Use:

## SQLite

Reasons:

- zero external database server
- easy local deployment
- suitable for the current single-machine prototype
- persistent across process restarts
- easy to inspect during SIH demonstration
- straightforward migration path later

Do NOT introduce PostgreSQL, Redis, Kafka, Elasticsearch, or distributed infrastructure in M6 unless a demonstrated requirement exists.

---

# 24. Persistence Architecture

Business logic must not directly depend on SQL statements.

Use an abstraction:

```text
AlertManager
      ↓
AlertRepository
      ↓
SQLite
```

and:

```text
SecurityEventService
      ↓
SecurityEventRepository
      ↓
SQLite
```

This allows future replacement with a production database without rewriting the event engine.

---

# 25. SQLite Persistence Scope

Persist at minimum:

### Security events

```text
event_id
source_spatial_event_id
rule_id
event_type
severity
camera_id
track_id
timestamp
correlation_id
metadata
created_at
```

### Alerts

```text
alert_id
severity
event_type
camera_id
track_id
rule_id
spatial_object_id
status
title
description
correlation_id
created_at
updated_at
resolved_at
metadata
```

The schema must use indexes for common lookups.

---

# 26. Restart Recovery

Test:

```text
process running
 ↓
OPEN alert exists
 ↓
process stops
 ↓
process restarts
 ↓
OPEN alert is recovered from SQLite
```

The system must not silently lose active alerts.

Likewise, resolved historical events must remain queryable after restart.

---

# 27. Alert Reopening

When an alert condition genuinely ends:

```text
OPEN
 ↓
RESOLVED
```

If the same condition later occurs again:

```text
new source event
 ↓
new SecurityEvent
 ↓
new Alert
```

The old resolved alert remains historical.

---

# 28. Alert Metadata

An alert should preserve:

```text
alert_id
security_event_id(s)
camera_id
track_id
rule_id
event_type
severity
created_at
updated_at
status
title
description
correlation_id
metadata
```

Do not store raw video frames inside the alert model.

---

# 29. Event Logging

Every interpreted event must be auditable.

Minimum information:

```text
timestamp
event_id
source_event_id
rule_id
camera_id
track_id
event_type
severity
alert_id
```

Do not log raw tensors or full video frames.

---

# 30. Evidence Boundary

M6 should preserve metadata useful for future evidence extraction:

```text
camera_id
frame_id where available
timestamp
track_id
```

Future milestones may use this to retrieve:

- pre-event frames
- event snapshots
- post-event clips

M6 does not implement evidence extraction.

---

# 31. Real-Time Processing

M6 must not perform expensive computer vision.

Pipeline:

```text
M5 event
   ↓
normalize
   ↓
rules
   ↓
correlation
   ↓
SecurityEvent
   ↓
Alert
```

Target performance:

```text
Average event interpretation latency < 2 ms
Maximum event interpretation latency < 10 ms
```

These are benchmark targets, not assumptions.

If targets are missed, report the actual values and investigate the bottleneck rather than hiding the result.

---

# 32. Backpressure

M6 is different from M2.

M2 may intentionally drop stale video frames.

M6 must **not silently drop security events**.

If event processing becomes slower than event arrival:

- use a bounded event queue
- expose queue depth
- apply a documented failure/overflow policy
- preserve event ordering
- log failures
- fail visibly rather than silently discarding security events

A security event is more important than a stale video frame.

---

# 33. Event Queue

Conceptual:

```text
M5
 ↓
SpatialEvent Queue
 ↓
M6 Normalizer
 ↓
Rule Engine
 ↓
SecurityEvent
 ↓
Alert Manager
 ↓
SQLite
```

Metrics:

- events received
- events processed
- malformed events
- rules evaluated
- rules matched
- security events generated
- correlations created
- alerts created
- duplicates suppressed
- processing latency
- queue depth
- persistence failures

---

# 34. Failure Isolation

If one rule fails:

```text
Rule A → exception
Rule B → still executes
Rule C → still executes
```

Likewise:

- malformed event must not stop later events
- one camera's event must not stop another camera
- one persistence failure must be observable
- one correlation failure must not stop rule processing

All errors must be logged with enough context to diagnose them.

---

# 35. Configuration

M6 policy must be externally configurable.

Do not hardcode:

- severity
- restricted zones
- rule IDs
- camera scopes
- alert policies
- deduplication policies
- correlation windows
- correlation relationships

Use a human-readable, versionable structured configuration.

---

# 36. Configuration Validation

Validate before runtime where possible.

Reject:

- missing rule ID
- duplicate rule ID
- invalid event type
- invalid severity
- invalid direction
- invalid alert policy
- invalid correlation policy
- non-positive correlation window
- impossible rule combinations

Invalid rules must not silently disappear.

---

# 37. Rule Priority & Exclusivity

Rules should support priority.

If multiple rules match:

```text
Rule A priority 10
Rule B priority 20
```

both may execute by default.

If a rule explicitly declares an exclusive policy, the configured priority can determine which rule wins.

Do not invent exclusivity behavior implicitly.

---

# 38. Demonstration Rule Set

Create a small deterministic rule set.

### Rule 1 — Restricted Zone Entry

```text
Event:
ZONE_ENTER

Zone:
zone_01

Result:
RESTRICTED_ZONE_ENTRY

Severity:
HIGH
```

### Rule 2 — Restricted Boundary Crossing

```text
Event:
LINE_CROSS

Line:
line_01

Direction:
configured direction

Result:
BORDER_LINE_CROSSING

Severity:
CRITICAL
```

### Rule 3 — Restricted Zone Exit

```text
Event:
ZONE_EXIT

Zone:
zone_01

Result:
RESTRICTED_ZONE_EXIT

Severity:
LOW or INFO
```

These are demonstration policies only.

---

# 39. Policy Principle

Do not assume:

```text
ZONE_ENTER = INTRUSION
```

or:

```text
LINE_CROSS = THREAT
```

M5 reports what happened geometrically.

M6 determines meaning only through configuration.

For example:

```text
parking_zone
```

may produce no alert.

Whereas:

```text
restricted_border_zone
```

may produce HIGH severity.

---

# 40. Deduplication Tests

Implement deterministic tests for:

### Case A
One spatial event → one security event.

### Case B
Same source event + same rule processed twice → one logical security event.

### Case C
Same active condition persists → no alert storm.

### Case D
Two different matching rules → two legitimate security events/alerts unless explicitly configured as exclusive.

### Case E
Condition resolves → alert resolves.

### Case F
Same condition genuinely occurs again after resolution → new alert.

---

# 41. Correlation Tests

Test:

### Case A
Two related events from same track/camera within 5 seconds → one correlation context.

### Case B
Related events beyond 5 seconds → separate contexts.

### Case C
Same timestamps but different tracks → no correlation unless explicitly configured.

### Case D
Same track but different cameras → no cross-camera correlation in M6.

### Case E
Unrelated event types → no correlation.

### Case F
Correlation disabled by configuration → events remain independent.

---

# 42. Rule Engine Tests

Test:

- matching event type
- wrong event type
- matching camera
- wrong camera
- matching zone
- wrong zone
- matching direction
- wrong direction
- enabled rule
- disabled rule
- known object class
- unknown object class
- multiple matching rules
- exclusive rule
- malformed rule
- malformed event

All tests must be deterministic.

---

# 43. Alert Lifecycle Tests

Test:

```text
OPEN
→ ACKNOWLEDGED
→ RESOLVED
```

Also:

```text
OPEN
→ RESOLVED
→ process restart
→ historical state remains
→ new occurrence
→ new OPEN alert
```

Also verify that:

```text
OPEN
```

alerts are recovered after restart.

---

# 44. Persistence Tests

Test:

1. create security event
2. create alert
3. stop process
4. restart process
5. retrieve event
6. retrieve alert
7. verify status
8. verify metadata
9. verify timestamps
10. verify source-event relationship

SQLite must preserve state correctly.

---

# 45. Real-Video Validation

Use the canonical:

```text
videoplayback.mp4
```

Do not change M3/M4/M5 configurations.

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
```

Verify that actual M5 events are interpreted according to the configured rules.

Example:

```text
ZONE_ENTER zone_01
        ↓
RESTRICTED_ZONE_ENTRY
        ↓
HIGH alert
```

and:

```text
LINE_CROSS line_01 A_TO_B
        ↓
BORDER_LINE_CROSSING
        ↓
CRITICAL alert
```

Do not invent event counts. Report exactly what the run produces.

---

# 46. M5 Regression Protection

Before declaring M6 complete, verify:

- M5 still emits the same spatial events
- zone hysteresis remains unchanged
- tripwire behavior remains unchanged
- track IDs remain unchanged
- M5 source code was not unnecessarily modified
- M6 consumes M5 events rather than replacing them

M5 is frozen.

---

# 47. Performance Benchmark

Measure M6 independently.

Record:

```text
events_received
events_processed
rules_evaluated
rules_matched
security_events_generated
correlations_created
alerts_created
duplicates_suppressed
avg_event_processing_ms
max_event_processing_ms
queue_depth_max
sqlite_write_latency
```

Compare actual results with:

```text
Average < 2 ms
Maximum < 10 ms
```

targets.

---

# 48. Persistence Choice

M6 uses:

```text
SQLite
```

for the prototype.

Do not introduce:

- PostgreSQL
- Redis
- Kafka
- Elasticsearch/OpenSearch
- distributed event buses

unless a measured requirement appears.

The repository abstraction must allow future migration.

---

# 49. API Boundary

Do not build the full frontend.

Expose a clean future-facing service boundary for:

```text
submit SpatialEvent
get SecurityEvent
get Active Alerts
acknowledge Alert
resolve Alert
```

The implementation may remain minimal.

Future dashboards must not access internal rule-engine state directly.

---

# 50. Observability

Expose:

```text
events/sec
rule evaluation latency
security events/sec
correlations/sec
alerts/sec
duplicate suppression count
queue depth
processing failures
active alerts
SQLite persistence failures
```

Use existing project logging/configuration infrastructure.

---

# 51. Security & Reliability

The engine must:

- fail safely for malformed rules
- fail safely for malformed events
- avoid silent security-event loss
- preserve source-event traceability
- isolate rule failures
- bound memory
- prevent unbounded alert accumulation
- validate configuration
- persist alert state
- produce auditable logs

---

# 52. Privacy Considerations

M6 must not introduce new biometric processing.

No face recognition or identity inference is part of M6.

Only upstream identifiers such as:

```text
camera_id
track_id
```

are carried forward.

Future biometric milestones require separate data-governance decisions.

---

# 53. Testing Strategy

### Level 1 — Unit

- normalization
- rule matching
- severity
- security-event creation
- deduplication
- correlation
- alert lifecycle
- configuration validation

### Level 2 — Integration

```text
M5 SpatialEvent
 ↓
M6 Normalizer
 ↓
Rule Engine
 ↓
Correlation
 ↓
SecurityEvent
 ↓
Alert
 ↓
SQLite
```

### Level 3 — Persistence/Restart

Verify state survives process restart.

### Level 4 — Stress

Generate many events and verify:

- bounded queue
- no memory leak
- stable latency
- deterministic ordering
- no silent event loss

### Level 5 — Real Video

Run the complete canonical pipeline on:

```text
videoplayback.mp4
```

---

# 54. Acceptance Criteria

M6 is complete only when:

## Architecture

- [ ] M5 remains unchanged/frozen
- [ ] M6 consumes `SpatialEvent[]`
- [ ] M6 produces canonical security events
- [ ] detector/tracker internals remain isolated

## Rules

- [ ] configurable rule engine
- [ ] event-type matching
- [ ] camera matching
- [ ] spatial-object matching
- [ ] direction matching
- [ ] object-class handling with UNKNOWN
- [ ] enabled/disabled rules
- [ ] deterministic evaluation
- [ ] priority/exclusivity behavior

## Correlation

- [ ] basic correlation implemented
- [ ] default demonstration window = 5 seconds
- [ ] configurable window
- [ ] same-camera/track context
- [ ] no advanced behavioral inference
- [ ] correlation tests pass

## Security Events

- [ ] stable event identity
- [ ] severity
- [ ] source-event traceability
- [ ] metadata
- [ ] timestamps
- [ ] correlation ID where applicable

## Alerts

- [ ] alert creation
- [ ] deduplication
- [ ] multi-rule behavior validated
- [ ] OPEN
- [ ] ACKNOWLEDGED
- [ ] RESOLVED
- [ ] new alert after genuine recurrence
- [ ] restart recovery

## Persistence

- [ ] SQLite implemented
- [ ] security events persisted
- [ ] alerts persisted
- [ ] indexes created
- [ ] restart recovery verified
- [ ] repository abstraction present

## Reliability

- [ ] malformed events isolated
- [ ] malformed rules isolated
- [ ] bounded event queue
- [ ] deterministic ordering
- [ ] no silent event loss
- [ ] persistence failures observable

## Testing

- [ ] unit tests
- [ ] rule tests
- [ ] multi-rule tests
- [ ] correlation tests
- [ ] deduplication tests
- [ ] alert lifecycle tests
- [ ] persistence/restart tests
- [ ] integration tests
- [ ] stress tests
- [ ] canonical real-video test

## Performance

- [ ] average event latency measured
- [ ] maximum event latency measured
- [ ] queue depth measured
- [ ] SQLite write latency measured
- [ ] target comparison reported

## Scope

- [ ] no ANPR
- [ ] no face recognition
- [ ] no suspicious-activity ML
- [ ] no night detection
- [ ] no cross-camera Re-ID
- [ ] no command-center UI
- [ ] no M7+ functionality

---

# 55. M6 Completion Report Requirements

When implementation is complete, Antigravity must produce:

1. architecture implemented
2. files/modules added or changed
3. rule configuration design
4. SecurityEvent contract
5. Alert contract
6. alert lifecycle
7. deduplication strategy
8. basic correlation strategy
9. event normalization
10. SQLite schema/persistence design
11. restart-recovery results
12. error handling
13. unit-test results
14. rule-test results
15. correlation-test results
16. alert-lifecycle results
17. persistence-test results
18. integration-test results
19. stress-test results
20. real-video results
21. M5 regression results
22. performance metrics
23. object-class availability at the M5→M6 boundary
24. known limitations
25. dependency/license changes
26. final acceptance checklist
27. final M6 status

Do not mark M6 complete without evidence.

---

# 56. M7+ Forward Reference

M6 deliberately establishes the foundation for future behavioral intelligence.

Future milestones should build on:

```text
SpatialEvent
      ↓
SecurityEvent
      ↓
Correlation Context
      ↓
Alert
```

M7 and later milestones may add:

- loitering
- suspicious activity
- behavioral patterns
- temporal activity analysis
- advanced multi-event correlation
- night movement intelligence

They must extend the M6 event/correlation infrastructure rather than creating a second independent event system.

M6's basic correlation is therefore an intentional extension point, not the final behavioral engine.

---

# 57. Implementation Discipline

Build incrementally:

```text
Step 1
Domain contracts
        ↓
Step 2
Event normalization
        ↓
Step 3
Rule representation
        ↓
Step 4
Rule engine
        ↓
Step 5
SecurityEvent generation
        ↓
Step 6
Basic correlation
        ↓
Step 7
Alert manager
        ↓
Step 8
Deduplication
        ↓
Step 9
SQLite persistence
        ↓
Step 10
Restart recovery
        ↓
Step 11
Unit/integration tests
        ↓
Step 12
Real-video validation
        ↓
Step 13
Performance benchmark
        ↓
M6 completion report
```

Do not implement everything in one uncontrolled change.

After each major component, validate it before moving forward.

---

# 58. Final Instruction to Antigravity

You are now starting **M6**.

M1–M5 are frozen.

Do not modify completed milestones unless a reproducible integration defect is discovered and explicitly documented.

Start strictly from:

```text
SpatialEvent[]
```

Build:

```text
Normalization
 ↓
Rule Engine
 ↓
SecurityEvent
 ↓
Basic 5-second Correlation
 ↓
Alert Manager
 ↓
SQLite Persistence
```

The first implementation must remain:

- modular
- rule-driven
- deterministic
- testable
- lightweight
- auditable
- configuration-driven
- restart-safe
- independent of YOLO/ByteTrack/OpenCV internals

Do not implement:

- ANPR
- face recognition
- suspicious-activity ML
- night detection
- cross-camera Re-ID
- command-center UI
- advanced behavioral reasoning

Do not silently drop security events.

Do not use an in-memory-only alert store.

Do not treat multiple matching rules as accidental duplicates.

Do not implement advanced correlation; M6 only implements the defined basic configurable correlation mechanism.

Do not skip validation.

Do not proceed to M7.

After completing the M6 acceptance tests, produce the required completion report and STOP.

**M6 begins here.**
