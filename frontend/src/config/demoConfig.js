/**
 * SIH Selection Demo Mode Configuration
 * =======================================
 * Contains isolated presentation data to populate the Command Center safely
 * without running AI inference or polluting the production event database.
 */

// Toggle this via .env file: VITE_IBVAP_DEMO_MODE=true
export const IS_DEMO_MODE = import.meta.env.VITE_IBVAP_DEMO_MODE === 'true';

// Configurable video paths (served from /public or external URL)
export const DEMO_VIDEOS = {
    CAM_1: import.meta.env.VITE_DEMO_VIDEO_1 || "/videos/demo1.mp4",
    CAM_2: import.meta.env.VITE_DEMO_VIDEO_2 || "/videos/demo2.mp4",
    CAM_3: import.meta.env.VITE_DEMO_VIDEO_3 || "/videos/demo3.mp4",
    CAM_4: import.meta.env.VITE_DEMO_VIDEO_4 || "/videos/demo4.mp4",
};

export const DEMO_CAMERAS = [
    { camera_id: "CAM-01", name: "BOP NORTH GATE", url: DEMO_VIDEOS.CAM_1, fps: 25, active_track_count: 3 },
    { camera_id: "CAM-02", name: "CHECK POST ALPHA", url: DEMO_VIDEOS.CAM_2, fps: 30, active_track_count: 5 },
    { camera_id: "CAM-03", name: "PERIMETER EAST", url: DEMO_VIDEOS.CAM_3, fps: 24, active_track_count: 1 },
    { camera_id: "CAM-04", name: "BORDER ROAD 01", url: DEMO_VIDEOS.CAM_4, fps: 30, active_track_count: 2 },
];

export const DEMO_ANPR_READS = [
    { event_id: "demo-a1", plate_text: "MH20XX1234", camera_id: "CAM-01", vehicle_class: "CAR", timestamp: new Date().toISOString() },
    { event_id: "demo-a2", plate_text: "MH12AB4589", camera_id: "CAM-02", vehicle_class: "MOTORCYCLE", timestamp: new Date(Date.now() - 60000).toISOString() },
    { event_id: "demo-a3", plate_text: "DL8CXX9999", camera_id: "CAM-01", vehicle_class: "TRUCK", timestamp: new Date(Date.now() - 300000).toISOString() },
];

export const DEMO_INCIDENTS_POOL = [
    {
        alert_id: "demo-inc-1",
        event_type: "RESTRICTED_AREA_INTRUSION",
        title: "RESTRICTED AREA INTRUSION",
        severity: "CRITICAL",
        camera_id: "CAM-01",
        track_id: "14",
        status: "OPEN"
    },
    {
        alert_id: "demo-inc-2",
        event_type: "FENCE_CROSSING",
        title: "FENCE CROSSING",
        severity: "HIGH",
        camera_id: "CAM-03",
        track_id: "9",
        status: "OPEN"
    },
    {
        alert_id: "demo-inc-3",
        event_type: "LOITERING",
        title: "SUSPICIOUS LOITERING",
        severity: "MEDIUM",
        camera_id: "CAM-02",
        track_id: "42",
        status: "OPEN"
    },
    {
        alert_id: "demo-inc-4",
        event_type: "NIGHT_MOVEMENT",
        title: "NIGHT MOVEMENT DETECTED",
        severity: "HIGH",
        camera_id: "CAM-04",
        track_id: "8",
        status: "OPEN"
    }
];
