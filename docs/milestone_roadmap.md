# IBVAP — Milestone Roadmap

| Milestone | Title | Key Deliverable |
|-----------|-------|----------------|
| **1** ✅ | Foundation & Architecture | Project structure, domain contracts, API boundary, logging, config |
| 2 | Video Ingestion | Frame acquisition from file → webcam → RTSP |
| 3 | Object Detection | YOLO integration, Detection domain objects, FPS measurement |
| 4 | Multi-Object Tracking | ByteTrack integration, persistent track IDs, trajectories |
| 5 | Spatial Intelligence | Polygon zones, virtual lines, containment/crossing logic |
| 6 | Event Engine | Intrusion, line-crossing, zone-entry, vehicle events |
| 7 | Loitering & Temporal Behavior | Dwell-time tracking, loitering event generation |
| 8 | ANPR | Plate detection → crop → OCR → normalization → event |
| 9 | Face Detection | Isolated face detection module (no recognition yet) |
| 10 | Night-Time Analytics | Low-light preprocessing, benchmark before/after |
| 11 | Suspicious Activity | Rule-based suspicious behavior patterns |
| 12 | Risk Engine | Scored severity with contributing factors and explanation |
| 13 | Evidence Management | Snapshot + clip capture per significant event |
| 14 | Backend & Persistence | PostgreSQL, camera/event/alert APIs, auth foundation |
| 15 | Real-Time Dashboard | Operator UI: live cameras, alerts, history, event details |
| 16 | Camera/Zone Configuration | Operator-configurable zones, lines, thresholds |
| 17 | Multi-Camera Intelligence | Parallel camera processing; future cross-camera analytics |
| 18 | Performance Optimization | ONNX, TensorRT, batching — after bottleneck measurement |
| 19 | Deployment | Docker, edge deployment, monitoring, health checks |
| 20 | Final Validation | Realistic scenarios, accuracy measurement, load testing |
