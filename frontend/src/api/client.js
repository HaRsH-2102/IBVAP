/**
 * IBVAP Frontend — API Client
 * ============================
 * Centralized HTTP client for all backend API calls.
 *
 * Configuration:
 *   - Base URL: http://localhost:8000 (development)
 *   - All requests include appropriate headers
 *   - Future: authentication token injection
 *
 * Note: Most API endpoints return 501 Not Implemented in Milestone 1.
 * This client is the architectural boundary for all backend communication.
 *
 * Future (Milestone 14+):
 *   - Add authentication header injection
 *   - Add request/response interceptors for error handling
 *   - Add retry logic for transient failures
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_VERSION = import.meta.env.VITE_API_VERSION || "v1";

export const API_URL = `${API_BASE_URL}/api/${API_VERSION}`;
export const WS_URL = `${API_BASE_URL.replace("http", "ws")}/ws`;

/**
 * Fetch wrapper with standard error handling.
 */
async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  return response;
}

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export const systemApi = {
  /** GET /api/v1/system/health */
  health: () => apiFetch("/system/health"),

  /** GET /api/v1/system/status */
  status: () => apiFetch("/system/status"),

  /** GET /api/v1/system/metrics */
  metrics: () => apiFetch("/system/metrics"),
};

// ---------------------------------------------------------------------------
// Cameras
// ---------------------------------------------------------------------------

export const cameraApi = {
  list: () => apiFetch("/cameras"),
  get: (id) => apiFetch(`/cameras/${id}`),
  register: (data) => apiFetch("/cameras", { method: "POST", body: JSON.stringify(data) }),
  update: (id, data) => apiFetch(`/cameras/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id) => apiFetch(`/cameras/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

export const eventApi = {
  list: (params = {}) => apiFetch("/events?" + new URLSearchParams(params)),
  get: (id) => apiFetch(`/events/${id}`),
  summary: () => apiFetch("/events/summary"),
  getEvidence: (id) => apiFetch(`/events/${id}/evidence`),
  overridePlate: (id, data) => apiFetch(`/events/${id}/override_plate`, { method: "POST", body: JSON.stringify(data) }),
};

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export const alertApi = {
  listActive: () => apiFetch("/alerts"),
  summary: () => apiFetch("/alerts/summary"),
  get: (id) => apiFetch(`/alerts/${id}`),
  acknowledge: (id, operatorId) =>
    apiFetch(`/alerts/${id}/ack`, {
      method: "PATCH",
      body: JSON.stringify({ operator_id: operatorId }),
    }),
  resolve: (id, operatorId, notes) =>
    apiFetch(`/alerts/${id}/resolve`, {
      method: "PATCH",
      body: JSON.stringify({ operator_id: operatorId, notes }),
    }),
};

// ---------------------------------------------------------------------------
// ANPR
// ---------------------------------------------------------------------------

export const anprApi = {
  list: (params = {}) => apiFetch("/anpr/reads?" + new URLSearchParams(params)),
  summary: () => apiFetch("/anpr/summary"),
  status: () => apiFetch("/anpr/status"),
  search: (plate) => apiFetch(`/anpr/reads/${plate}`),
  getEvidenceUrl: (eventId, imageType) => `${API_URL}/anpr/evidence/${eventId}/${imageType}`
};

// ---------------------------------------------------------------------------
// Zones & Virtual Lines
// ---------------------------------------------------------------------------

export const zoneApi = {
  list: (cameraId) => apiFetch(`/zones${cameraId ? '?camera_id=' + cameraId : ''}`),
  create: (data) => apiFetch('/zones', { method: 'POST', body: JSON.stringify(data) }),
  get: (id) => apiFetch(`/zones/${id}`),
  update: (id, data) => apiFetch(`/zones/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  remove: (id) => apiFetch(`/zones/${id}`, { method: 'DELETE' }),
  listLines: (cameraId) => apiFetch(`/zones/lines${cameraId ? '?camera_id=' + cameraId : ''}`),
  createLine: (data) => apiFetch('/zones/lines', { method: 'POST', body: JSON.stringify(data) }),
  updateLine: (id, data) => apiFetch(`/zones/lines/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  removeLine: (id) => apiFetch(`/zones/lines/${id}`, { method: 'DELETE' }),
};

// ---------------------------------------------------------------------------
// Videos
// ---------------------------------------------------------------------------

export const videoApi = {
  list: () => apiFetch("/videos"),
  get: (id) => apiFetch(`/videos/${id}`),
  create: (data) => apiFetch("/videos", { method: "POST", body: JSON.stringify(data) }),
  delete: (id) => apiFetch(`/videos/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export const analyticsApi = {
  summary: () => apiFetch("/analytics/summary"),
  trends: () => apiFetch("/analytics/trends"),
};

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

export const validationApi = {
  status: () => apiFetch('/validation/status'),
  start: (video_id) => apiFetch('/validation/start', { method: 'POST', body: JSON.stringify({ video_id }) }),
  stop: () => apiFetch('/validation/stop', { method: 'POST' }),
  pause: () => apiFetch('/validation/pause', { method: 'POST' }),
  play: () => apiFetch('/validation/play', { method: 'POST' }),
  setSpeed: (speed) => apiFetch('/validation/speed', { method: 'POST', body: JSON.stringify({ speed }) }),
  seek: (timestamp_sec) => apiFetch('/validation/seek', { method: 'POST', body: JSON.stringify({ timestamp_sec }) })
};

// ---------------------------------------------------------------------------
// WebSocket Connection
// ---------------------------------------------------------------------------

/**
 * Create a WebSocket connection to the IBVAP real-time endpoint.
 *
 * @param {function} onMessage - Called with parsed JSON message objects
 * @param {function} onOpen - Called when connection is established
 * @param {function} onClose - Called when connection is closed
 * @returns {WebSocket}
 */
export function createWebSocketConnection(onMessage, onOpen, onClose) {
  const ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log("[IBVAP] WebSocket connected");
    if (onOpen) onOpen();
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onMessage) onMessage(data);
    } catch (e) {
      console.warn("[IBVAP] Received non-JSON WebSocket message", event.data);
    }
  };

  ws.onclose = (event) => {
    console.log("[IBVAP] WebSocket disconnected", event.code);
    if (onClose) onClose(event);
  };

  ws.onerror = (error) => {
    console.error("[IBVAP] WebSocket error", error);
  };

  return ws;
}
