# IBVAP
**Intelligent Border Video Analytics Platform**

An AI-Based Intelligent Video Analytics Platform designed for rigorous border surveillance using existing CCTV infrastructure. IBVAP integrates cutting-edge spatial and behavioral intelligence, temporal analysis, and real-time alerts to augment security operator awareness.

---

## 1. Overview
The Intelligent Border Video Analytics Platform (IBVAP) is an advanced video analytics system built for comprehensive surveillance monitoring. It bridges the gap between passive video recording and active AI-driven threat detection, ingesting IP CCTV streams to process real-time spatial and behavioral analytics.

## 2. Problem Statement
Traditional border surveillance relies heavily on human operators monitoring multiple screens, leading to fatigue, delayed response times, and missed critical events. Existing infrastructure often lacks the necessary intelligence to autonomously detect intrusions, loitering, or suspicious behaviors across vast and complex environments, especially under adverse lighting conditions.

## 3. Solution
IBVAP addresses these challenges by layering a sophisticated AI intelligence pipeline over existing CCTV networks. By utilizing state-of-the-art object detection (RT-DETR-L), robust multi-object tracking (ByteTrack), and a highly configurable rule engine, IBVAP autonomously identifies security breaches, tracks threats, and issues real-time alerts to operators through a high-performance web dashboard.

## 4. Key Features
- **Real-Time Video Ingestion:** Seamless integration with RTSP/IP CCTV feeds.
- **Advanced Object Detection & Tracking:** Powered by RT-DETR-L and ByteTrack for robust temporal coherence.
- **Configurable Spatial Zones:** Define virtual fences and restricted areas.
- **Behavioral Intelligence:** Detect loitering, group formations, and suspicious activities.
- **Night-Time Intelligence:** Adaptive thresholds and luminance checks for 24/7 reliability.
- **ANPR System:** Real-time Automatic Number Plate Recognition and vehicle context tracking.
- **Live Command Center:** A React-based, WebSocket-powered interactive dashboard.
- **Evidence Management:** Automatic retention of critical frames and bounding-box crops.

## 5. System Architecture
IBVAP consists of two highly decoupled subsystems:
1. **The Intelligence Engine (Backend):** A Python + FastAPI application handling stream ingestion, AI inference (CUDA/PyTorch), rule evaluation, event generation, and WebSocket broadcasting.
2. **The Command Center (Frontend):** A React + Vite application that visualizes telemetry, renders bounding boxes over streams, and manages incidents.

## 6. AI/ML Pipeline
The pipeline operates strictly in real-time, transitioning from pixel ingestion to semantic understanding:
`IP CCTV → Frame Buffer → RT-DETR-L Inference → Confidence Gating → ByteTrack → Spatial Validation → Behavioral Rules → Event Dispatcher`

## 7. Object Detection — RT-DETR-L
IBVAP employs **RT-DETR-L** (Real-Time DEtection TRansformer) as its primary perception engine. This provides transformer-level accuracy while maintaining real-time processing speeds.

## 8. Multi-Object Tracking — ByteTrack
To maintain temporal coherence across frames, **ByteTrack** associates bounding boxes over time, assigning persistent Track IDs. This is vital for behavioral rules like loitering, which depend on measuring an object's dwell time.

## 9. Spatial Intelligence
Operators can define geometric rules (Virtual Lines for fence-crossing, Polygons for restricted areas). The spatial engine computes intersections between tracked object bounding boxes and these virtual boundaries to trigger events.

## 10. Behavioral Intelligence
The engine tracks long-term object state, identifying anomalous behaviors such as extended loitering in sensitive zones or suspicious directional movement.

## 11. Rule Engine
A dynamic rule engine evaluates detections against configured scenarios. Rules are bound to specific cameras and object classes, ensuring that alerts are only generated when specific criteria (e.g., "Person" + "Fence Crossing" + "Night Time") are met.

## 12. Security Events & Alerts
When a rule triggers, a `SecurityEvent` is created. If the event breaches a severity threshold, an actionable `Alert` is dispatched to the Command Center via WebSockets for immediate operator intervention.

## 13. Evidence Management
IBVAP automatically extracts and stores forensic evidence. This includes the full raw frame, the annotated frame (with bounding boxes), and isolated crops of the offending object, managed through a dedicated SQLite persistence layer.

## 14. ANPR Pipeline
The Automatic Number Plate Recognition (ANPR) pipeline uses a dedicated YOLO11 plate detector (`best.pt`) combined with OCR to identify vehicle registrations entering or exiting secured zones. It utilizes temporal consensus to ensure accuracy across multiple frames.

## 15. ANPR Benchmark Summary
Our ANPR pipeline has been benchmarked using annotated datasets specifically curated for Indian license plates.
- **Plate Detection:** High accuracy utilizing YOLO11 (`best.pt`).
- **OCR Engine:** Awiros/PaddleOCR was selected over EasyOCR due to superior character-level accuracy and robustness.
- **Metrics:** We differentiate between raw plate detection metrics, character-level OCR accuracy, and exact-match normalized accuracy.

*(Note: IBVAP does not claim 100% real-world detection accuracy, as performance is highly dependent on environmental factors, camera angles, and lighting).*

## 16. Backend Architecture
Built with **Python and FastAPI**, the backend leverages asynchronous I/O and thread pools to ensure the heavy AI inference loop does not block API requests or WebSocket telemetry broadcasts.

## 17. Frontend Architecture
The frontend is a modern SPA built with **React and Vite**, styled with standard CSS. It features a responsive layout, live video playback, and dynamic telemetry overlays, optimized for operator efficiency.

## 18. Database
IBVAP utilizes **SQLite** for configuration and operational state management (events, alerts, ANPR reads, evidence mapping). The schema is managed via automated startup migrations.

## 19. Real-Time WebSocket Communication
A robust WebSocket implementation streams live metrics, detection bounding boxes, system health, and critical alerts from the backend directly to the React frontend at high refresh rates.

## 20. Demo Mode
IBVAP includes a built-in Demo Mode utilizing pre-recorded video assets (`demo1.mp4` to `demo4.mp4`). This provides a fully interactive simulation of the Command Center without requiring live RTSP camera feeds, perfect for evaluations and presentations.

## 21. Technology Stack
- **Backend:** Python, FastAPI, PyTorch, OpenCV, SQLite
- **Frontend:** React, Vite, standard CSS
- **AI/ML:** RT-DETR-L, ByteTrack, YOLO11, PaddleOCR
- **Hardware:** CUDA / FP16 optimized for NVIDIA GPUs

## 22. Project Structure
```text
IBVAP/
├── ANPR/                 # Standalone ANPR testing & OCR environments
├── backend/              # FastAPI server & AI Intelligence Engine
├── docs/                 # Extended documentation and milestone reports
├── frontend/             # React Command Center UI
├── models/               # Excluded AI model weights directory
├── .env.example          # Environment configuration template
├── .gitignore            # Git exclusion rules
└── README.md             # This file
```

## 23. Installation
Ensure Python 3.10+ and Node.js 18+ are installed.
1. Clone the repository.
2. Initialize the backend virtual environment and install dependencies.
3. Install frontend dependencies via `npm install`.

## 24. Environment Configuration
Copy `.env.example` to `.env` in the root directory. Update paths, specifically ensuring that `IBVAP_DETECTOR_MODEL_PATH` points to your downloaded model weights (refer to `models/README.md`).

## 25. Running Backend
Navigate to the `backend/` directory, activate the virtual environment, and run:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 26. Running Frontend
Navigate to the `frontend/` directory and run:
```bash
npm run dev
```

## 27. GPU/CUDA Requirements
To achieve real-time processing (e.g., 25+ FPS), a dedicated NVIDIA GPU with CUDA support is highly recommended. The system will fall back to CPU processing, but at significantly reduced frame rates.

## 28. Configuration
System behaviors (thresholds, loitering times, camera limits) can be configured via environment variables or the `.env` file as defined in `backend/app/config.py`.

## 29. Testing
Basic backend validation can be performed by running `python -m compileall backend` or executing the internal test scripts.

## 30. Deployment
Currently configured for local/on-premise deployment. Containerization via Docker is planned for future releases.

## 31. Future Enhancements
- Full Docker containerization.
- Multi-node GPU distribution for processing >16 cameras.
- Cloud-based telemetry aggregation.

## 32. Team / Project Information
Developed for the **Smart India Hackathon 2026**.
