# IBVAP — Data Flow Contract

**Version:** Milestone 1  
**Status:** Contracts defined. Runtime flow not yet active (Milestones 2+ required).

---

## 1. Conceptual Data Flow

```
Video Source
    │
    │  [raw bytes / frames]
    ▼
VideoStream
    │
    │  [decoded frame]
    ▼
Frame
    │  camera_id, timestamp, width, height, frame_index
    │
    ▼
Detection  (one or more per frame)
    │  camera_id, frame_id, class, bounding_box, confidence, timestamp
    │
    ▼
Track  (persistent across frames)
    │  camera_id, track_id, class, trajectory, first_seen, last_seen
    │
    ▼
Spatial Observation  (Track × Zone/Line evaluation)
    │  is_inside_zone, has_crossed_line, direction, dwell_time
    │
    ▼
Event
    │  camera_id, event_type, track_id, zone_id, timestamp, severity
    │
    ▼
RiskAssessment
    │  risk_score, severity_level, contributing_factors, explanation
    │
    ▼
Alert
    │  alert_id, event_id, severity, state, created_at
    │
    ▼
Evidence
    │  evidence_id, event_id, type (snapshot/clip), file_ref, camera_id
    │
    ▼
Persistence (PostgreSQL — future)
    │  cameras, events, alerts, evidence metadata, tracks
    │
    ▼
REST API  →  HTTP clients, operator systems
WebSocket  →  real-time dashboard push

    ▼
Operator Dashboard
    │  Display alert, show camera feed, show event detail, acknowledge
    │
    ▼
Operator Action (acknowledge, investigate, resolve)
    │
    ▼
Audit Log
```

---

## 2. Domain Contract Definitions

### Camera

```
Camera
├── camera_id: str              Unique identifier
├── name: str                   Human-readable name
├── location: str               Physical/logical location
├── stream_config: dict         Source URL, auth config (from env)
├── status: CameraStatus        ACTIVE | INACTIVE | ERROR | UNKNOWN
├── capabilities: list[str]     Future: ["ptz", "infrared", "audio"]
├── configuration: dict         Processing parameters
├── zone_ids: list[str]         Associated zone identifiers
└── virtual_line_ids: list[str] Associated virtual line identifiers
```

### VideoStream

```
VideoStream
├── stream_id: str
├── camera_id: str
├── state: StreamState          CONNECTING | ACTIVE | PAUSED | ERROR | STOPPED
├── source_type: SourceType     FILE | WEBCAM | RTSP
├── source_url: str
├── resolution_width: int
├── resolution_height: int
├── fps: float
├── last_frame_at: datetime
└── error_message: str | None
```

### Frame

```
Frame
├── frame_id: str               UUID
├── camera_id: str
├── timestamp: datetime         Wall-clock time of capture
├── frame_index: int            Sequential index within stream
├── width: int
├── height: int
├── source_info: str            e.g. "rtsp://..." or "video_file.mp4"
└── data: bytes | None          Raw pixel data (populated during processing)
```

### Detection

```
Detection
├── detection_id: str           UUID
├── camera_id: str
├── frame_id: str
├── object_class: ObjectClass   PERSON | CAR | MOTORCYCLE | BUS | TRUCK | FACE | PLATE | UNKNOWN
├── bounding_box: BoundingBox   x1, y1, x2, y2 (pixel coordinates)
├── confidence: float           0.0 – 1.0
├── timestamp: datetime
├── model_name: str | None      e.g. "yolov8n", "retinaface"
└── extra_metadata: dict        Extensible for future fields
```

### Track

```
Track
├── track_id: str               Persistent ID across frames
├── camera_id: str
├── object_class: ObjectClass
├── bounding_box: BoundingBox   Current position
├── trajectory: list[TrackPoint] History of positions + timestamps
├── first_seen: datetime
├── last_seen: datetime
├── state: TrackState           ACTIVE | LOST | REMOVED
└── metadata: dict              Extra tracker-specific info
```

### Zone

```
Zone
├── zone_id: str
├── camera_id: str
├── name: str
├── zone_type: ZoneType         NORMAL | RESTRICTED | MONITORING | ENTRY | EXIT
├── geometry: list[Point]       Polygon vertices (pixel or normalized coordinates)
├── active: bool
└── configuration: dict         Future: time-of-day rules, object class filters
```

### VirtualLine

```
VirtualLine
├── line_id: str
├── camera_id: str
├── name: str
├── start: Point                Line start point
├── end: Point                  Line end point
├── allowed_direction: Direction  A_TO_B | B_TO_A | BOTH | NONE
├── active: bool
└── configuration: dict
```

### Event

```
Event
├── event_id: str               UUID
├── camera_id: str
├── event_type: EventType       INTRUSION | LOITERING | LINE_CROSSING | NIGHT_MOVEMENT
│                               VEHICLE_INTRUSION | ANPR_DETECTION | FACE_DETECTION
│                               WRONG_DIRECTION | COMPOUND
├── track_id: str | None
├── zone_id: str | None
├── line_id: str | None
├── timestamp: datetime
├── confidence: float
├── severity: SeverityLevel     LOW | MEDIUM | HIGH | CRITICAL
├── status: EventStatus         OPEN | ACKNOWLEDGED | CLOSED | SUPPRESSED
├── evidence_ids: list[str]     Associated evidence
└── metadata: dict              Event-specific details (dwell_time, plate_text, etc.)
```

### RiskAssessment

```
RiskAssessment
├── assessment_id: str
├── event_id: str
├── risk_score: float           0.0 – 100.0
├── severity: SeverityLevel
├── contributing_factors: list[str]  e.g. ["night_time", "restricted_zone", "extended_dwell"]
├── explanation: str            Human-readable explanation
└── rule_version: str           Version of the risk rule set used
```

### Alert

```
Alert
├── alert_id: str               UUID
├── event_id: str
├── severity: SeverityLevel
├── state: AlertState           DETECTED | ACTIVE | ACKNOWLEDGED | INVESTIGATING | RESOLVED
├── created_at: datetime
├── acknowledged_at: datetime | None
├── resolved_at: datetime | None
├── operator_id: str | None
└── notes: str | None
```

### Evidence

```
Evidence
├── evidence_id: str            UUID
├── event_id: str
├── camera_id: str
├── evidence_type: EvidenceType SNAPSHOT | VIDEO_CLIP | METADATA
├── file_reference: str | None  Storage path or object key
├── timestamp: datetime
├── retention_until: datetime | None  Future: configurable retention
└── metadata: dict
```

### SystemConfiguration

```
SystemConfiguration
├── log_level: str
├── api_host: str
├── api_port: int
├── cors_origins: list[str]
├── storage_base_path: str
├── evidence_retention_days: int
├── default_confidence_threshold: float
├── loitering_threshold_seconds: int
├── night_start_hour: int
├── night_end_hour: int
├── max_cameras: int
└── processing_fps_limit: int
```

---

## 3. Cross-Cutting Rules

1. **Every runtime object carries `camera_id`** — enables full data lineage from camera to alert.
2. **`frame_id` links detections to their source frame** — enables evidence association.
3. **`track_id` links events to their origin object** — enables multi-event correlation.
4. **`event_id` links alerts and evidence to their cause** — enables complete incident reconstruction.
5. **Timestamps use UTC** — localization happens at the dashboard display layer.
6. **Coordinates use pixel space** — normalized coordinates may be added for multi-resolution support.

---

## 4. What the Data Flow Is NOT

- **NOT request/response per image** — the final system processes continuous streams.
- **NOT camera-to-dashboard direct** — all intelligence happens in the processing pipeline.
- **NOT model-to-frontend direct** — AI results become domain objects before crossing API boundaries.
