import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { validationApi, videoApi, zoneApi } from '../api/client';
import { useWs } from '../api/ws';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export default function LiveValidation() {
    const navigate = useNavigate();
    const { status: wsStatus, events: wsEvents, isConnected } = useWs();
    
    // States: 'INITIALIZING', 'RUNNING', 'ERROR'
    const [viewState, setViewState] = useState('INITIALIZING');
    
    // Session State
    const [sessionId, setSessionId] = useState(null);
    const [selectedVideo, setSelectedVideo] = useState(null);
    
    // For rendering zones on the live video (purely visual in this screen)
    const [zones, setZones] = useState([]);
    const [lines, setLines] = useState([]);

    // 1. On Mount: Check if a session is already running
    useEffect(() => {
        const checkStatus = async () => {
            try {
                const res = await validationApi.status();
                if (res.ok) {
                    const data = await res.json();
                    if (data.is_running && data.video_id) {
                        setSessionId(data.session_id);
                        
                        // Fetch the video details
                        const vidRes = await videoApi.list();
                        if (vidRes.ok) {
                            const vids = await vidRes.json();
                            const activeVid = vids.find(v => v.id === data.video_id);
                            if (activeVid) setSelectedVideo(activeVid);
                        }
                        
                        // Fetch zones for visual overlay
                        const [zRes, lRes] = await Promise.all([
                            zoneApi.list(data.video_id),
                            zoneApi.listLines(data.video_id)
                        ]);
                        if (zRes.ok) setZones(await zRes.json());
                        if (lRes.ok) setLines(await lRes.json());
                        
                        setViewState('RUNNING');
                    } else {
                        // If no session running, redirect back to Zones for configuration
                        navigate('/zones');
                    }
                } else {
                    navigate('/zones');
                }
            } catch (e) {
                console.error("Failed to check validation status", e);
                navigate('/zones');
            }
        };
        checkStatus();
    }, [navigate]);

    const handleEditZones = async () => {
        try {
            await validationApi.pause();
            navigate('/zones');
        } catch (e) {
            console.error("Failed to pause", e);
            // Navigate anyway to allow editing
            navigate('/zones');
        }
    };

    const handleStop = async () => {
        try {
            await validationApi.stop();
            navigate('/zones');
        } catch (e) {
            console.error("Failed to stop", e);
            navigate('/zones');
        }
    };

    // Filter events to only show recent real ones
    const recentEvents = wsEvents
        .filter(e => e.type !== 'system' && e.type !== 'heartbeat')
        .slice(0, 50);

    const handleEventClick = (eventId) => {
        if (!eventId) return;
        navigate(`/alerts/${eventId}`);
    };

    const formatTimestamp = (ts) => {
        if (!ts) return 'Unknown Time';
        let d = new Date(ts);
        if (isNaN(d.getTime()) && typeof ts === 'string') {
            d = new Date(ts.replace(/(\.\d{3})\d+/, '$1'));
        }
        return isNaN(d.getTime()) ? 'Invalid Date' : d.toLocaleTimeString();
    };

    if (viewState === 'INITIALIZING') {
        return (
            <div className="flex h-full items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                    <span className="font-data-mono text-on-surface-variant tracking-widest text-sm">CONNECTING TO PIPELINE...</span>
                </div>
            </div>
        );
    }

    const latestFrameUrl = `${API_BASE_URL}/validation/stream?session=${sessionId}&t=${Date.now()}`;

    // Compute metrics
    const metrics = {
        fps: wsStatus?.pipeline_fps || 0,
        frames: wsStatus?.frames_processed || 0,
        active_tracks: wsStatus?.active_tracks || 0,
        persons: wsStatus?.persons || 0,
        vehicles: wsStatus?.vehicles || 0,
        events: wsStatus?.events_generated || 0
    };

    return (
        <div className="flex h-full bg-background overflow-hidden relative">
            <div className="flex-1 flex flex-col p-4 gap-4 overflow-hidden relative min-w-0">
                {/* Header Row */}
                <div className="flex justify-between items-end shrink-0">
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="font-headline-lg text-2xl font-bold text-on-surface tracking-tight">Live Surveillance</h1>
                            {isConnected ? (
                                <span className="bg-success/20 text-success border border-success/30 px-2 py-0.5 rounded text-[10px] font-bold tracking-widest font-data-mono flex items-center gap-1.5 shadow-[0_0_8px_rgba(45,212,191,0.2)]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
                                    LIVE
                                </span>
                            ) : (
                                <span className="bg-error/20 text-error border border-error/30 px-2 py-0.5 rounded text-[10px] font-bold tracking-widest font-data-mono flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
                                    DISCONNECTED
                                </span>
                            )}
                        </div>
                        <p className="font-body-md text-on-surface-variant mt-1 flex items-center gap-2">
                            <span className="material-symbols-outlined text-sm">videocam</span> {selectedVideo?.name}
                        </p>
                    </div>
                    
                    <div className="flex gap-2">
                        <button onClick={handleStop} className="px-4 py-2 border border-error/50 text-error rounded font-data-mono text-sm hover:bg-error/10 transition-colors">
                            STOP DEMO
                        </button>
                        <button onClick={handleEditZones} className="px-4 py-2 bg-secondary text-on-secondary rounded font-data-mono text-sm hover:brightness-110 transition-all flex items-center gap-2">
                            <span className="material-symbols-outlined text-[18px]">edit</span>
                            EDIT ZONES
                        </button>
                    </div>
                </div>

                {/* Video Area (Live Pipeline feed) */}
                <div className="flex-1 tech-panel overflow-hidden flex flex-col min-h-0 relative">
                    <div className="flex-1 bg-black relative flex items-center justify-center overflow-hidden border border-[#262C36] rounded-t-DEFAULT">
                        <img 
                            src={latestFrameUrl} 
                            className="max-w-full max-h-full object-contain pointer-events-none"
                            alt="Live Pipeline"
                            onError={(e) => { e.target.style.display = 'none'; }}
                            onLoad={(e) => { e.target.style.display = 'block'; }}
                        />
                    </div>
                    
                    {/* Bottom Metrics Bar */}
                    <div className="h-20 shrink-0 bg-[#151921] border-t border-[#262C36] flex">
                        <div className="px-4 py-2 border-r border-[#262C36] flex flex-col justify-center bg-[#1a1f29] min-w-[120px]">
                            <span className="font-label-caps text-on-surface-variant uppercase text-[10px] tracking-widest">Pipeline Status</span>
                            <span className="font-data-mono text-xs text-primary font-bold mt-1 tracking-wider">
                                {wsStatus?.ai_processing === 'RUNNING' ? 'ACTIVE' : 'IDLE'}
                            </span>
                        </div>
                        <div className="flex-1 flex divide-x divide-[#262C36]">
                            <div className="flex-1 p-3 flex flex-col justify-center items-center">
                                <span className="font-label-caps text-[9px] uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5 mb-1"><span className="material-symbols-outlined text-[14px]">speed</span> FPS</span>
                                <span className="font-data-mono text-lg text-on-surface">{metrics.fps.toFixed(1)}</span>
                            </div>
                            <div className="flex-1 p-3 flex flex-col justify-center items-center">
                                <span className="font-label-caps text-[9px] uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5 mb-1"><span className="material-symbols-outlined text-[14px]">route</span> TRACKS</span>
                                <span className="font-data-mono text-lg text-on-surface">{metrics.active_tracks}</span>
                            </div>
                            <div className="flex-1 p-3 flex flex-col justify-center items-center">
                                <span className="font-label-caps text-[9px] uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5 mb-1"><span className="material-symbols-outlined text-[14px]">person</span> PERSONS</span>
                                <span className="font-data-mono text-lg text-on-surface">{metrics.persons}</span>
                            </div>
                            <div className="flex-1 p-3 flex flex-col justify-center items-center">
                                <span className="font-label-caps text-[9px] uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5 mb-1"><span className="material-symbols-outlined text-[14px]">directions_car</span> VEHICLES</span>
                                <span className="font-data-mono text-lg text-on-surface">{metrics.vehicles}</span>
                            </div>
                            <div className="flex-1 p-3 flex flex-col justify-center items-center bg-error/5 group cursor-default">
                                <span className="font-label-caps text-[9px] uppercase tracking-wider text-error flex items-center gap-1.5 mb-1"><span className="material-symbols-outlined text-[14px]">bolt</span> EVENTS</span>
                                <span className="font-data-mono text-lg text-error font-bold">{metrics.events}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Sidebar: Live Events */}
            <div className="w-80 shrink-0 border-l border-outline flex flex-col bg-surface overflow-hidden relative z-10 shadow-[-8px_0_16px_rgba(0,0,0,0.2)]">
                <div className="px-4 py-3 border-b border-outline flex justify-between items-center bg-[#151921]">
                    <h2 className="font-label-caps text-[12px] text-on-surface-variant uppercase tracking-[0.1em] font-bold flex items-center gap-2">
                        <span className="material-symbols-outlined text-[16px]">list_alt</span>
                        Live Events
                    </h2>
                    <span className="bg-[#262C36] text-on-surface-variant px-2 py-0.5 rounded font-data-mono text-[10px]">
                        {recentEvents.length}
                    </span>
                </div>
                <div className="flex-1 overflow-y-auto p-3 space-y-2 relative">
                    {recentEvents.length === 0 ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-on-surface-variant opacity-50 p-6 text-center">
                            <span className="material-symbols-outlined text-4xl mb-2">monitoring</span>
                            <p className="font-body-sm">Listening for real-time security events...</p>
                        </div>
                    ) : (
                        recentEvents.map((evt, idx) => {
                            const isIntrusion = evt.type === 'INTRUSION';
                            const isLoitering = evt.type === 'LOITERING';
                            const isFence = evt.type === 'FENCE_CROSSING';
                            const isTailgating = evt.type === 'TAILGATING';
                            const isBehavior = evt.type === 'BEHAVIOR';
                            
                            const typeColor = 
                                isIntrusion ? 'text-error border-error bg-error/10' :
                                isLoitering ? 'text-warning border-warning bg-warning/10' :
                                isFence ? 'text-secondary border-secondary bg-secondary/10' :
                                'text-primary border-primary bg-primary/10';

                            return (
                                <button 
                                    key={evt.id || idx}
                                    onClick={() => handleEventClick(evt.event_id)}
                                    className="w-full text-left tech-panel p-3 rounded border border-[#262C36] bg-[#151921] hover:bg-surface-variant/20 hover:border-primary/50 transition-all flex flex-col gap-2 group"
                                >
                                    <div className="flex justify-between items-start">
                                        <span className={`text-[10px] uppercase font-bold font-data-mono px-1.5 py-0.5 rounded border ${typeColor} flex items-center gap-1`}>
                                            <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                                            {evt.type}
                                        </span>
                                        <span className="text-[10px] text-outline-variant font-data-mono">
                                            {formatTimestamp(evt.timestamp)}
                                        </span>
                                    </div>
                                    
                                    <div className="text-[11px] text-on-surface font-data-mono space-y-1">
                                        {(isIntrusion || isLoitering || isBehavior) && (
                                            <div>Zone: <span className="text-on-surface-variant">{evt.details?.zone_name || 'Unknown'}</span></div>
                                        )}
                                        {isFence && (
                                            <div>Fence: <span className="text-on-surface-variant">{evt.details?.line_name || 'Unknown'}</span></div>
                                        )}
                                        <div className="flex justify-between items-center mt-2">
                                            <span>TRK: <span className="text-primary">{evt.track_id}</span></span>
                                            {evt.evidence_saved ? (
                                                <span className="text-success text-[9px] flex items-center gap-1 uppercase tracking-wider bg-success/10 px-1.5 py-0.5 rounded border border-success/30 group-hover:bg-success group-hover:text-on-primary transition-colors">
                                                    <span className="material-symbols-outlined text-[12px]">image</span> Evidence
                                                </span>
                                            ) : (
                                                <span className="text-outline-variant text-[9px] flex items-center gap-1 uppercase tracking-wider">
                                                    FRM: {evt.frame_id}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </button>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
}
