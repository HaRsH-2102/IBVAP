import { useState, useEffect } from 'react';
import { useWs } from '../api/ws';
import { cameraApi, alertApi, anprApi, systemApi } from '../api/client';
import { useNavigate } from 'react-router-dom';
import { IS_DEMO_MODE, DEMO_CAMERAS, DEMO_ANPR_READS, DEMO_INCIDENTS_POOL } from '../config/demoConfig';

const CameraSnapshot = ({ camId, tick }) => {
    const [hasError, setHasError] = useState(false);
    const url = `http://127.0.0.1:8000/api/v1/cameras/${camId}/snapshot?t=${tick}`;
    
    useEffect(() => { setHasError(false); }, [tick]);

    return (
        <>
            {!hasError && (
                <img 
                    className="absolute inset-0 w-full h-full object-cover" 
                    src={url}
                    onError={() => setHasError(true)}
                    alt={`Camera ${camId}`}
                />
            )}
            {hasError && (
                <div className="flex flex-col items-center gap-2 text-outline-variant w-full h-full justify-center bg-surface-dim z-0 relative">
                    <span className="material-symbols-outlined text-[32px]">videocam_off</span>
                    <span className="font-data-mono text-[10px] text-center">FEED UNAVAILABLE</span>
                </div>
            )}
        </>
    );
};

const DemoCameraSnapshot = ({ cam }) => {
    return (
        <video 
            className="absolute inset-0 w-full h-full object-cover" 
            src={cam.url}
            autoPlay 
            loop 
            muted 
            playsInline
        />
    );
};

export default function Dashboard() {
    const navigate = useNavigate();
    const { status, events } = useWs();
    
    const [cameras, setCameras] = useState([]);
    const [alerts, setAlerts] = useState([]);
    const [anprReads, setAnprReads] = useState([]);
    
    const [metrics, setMetrics] = useState({
        totalCameras: 0,
        activeAlerts: 0,
        criticalAlerts: 0,
        anprTotal: 0,
    });
    
    const [snapshotTick, setSnapshotTick] = useState(0);

    const fetchData = async () => {
        if (IS_DEMO_MODE) {
            setCameras(DEMO_CAMERAS);
            setAnprReads(DEMO_ANPR_READS);
            return;
        }

        try {
            const [camRes, alertRes, anprRes, alertSumRes, anprSumRes] = await Promise.all([
                cameraApi.list(),
                alertApi.listActive(),
                anprApi.list({ limit: 5 }),
                alertApi.summary(),
                anprApi.summary(),
            ]);
            
            if (camRes.ok) setCameras(await camRes.json());
            if (alertRes.ok) {
                const alertsData = await alertRes.json();
                setAlerts(alertsData.filter(a => a.status === 'OPEN' || a.status === 'ACKNOWLEDGED').slice(0, 10));
            }
            if (anprRes.ok) setAnprReads(await anprRes.json());
            
            const alertSum = alertSumRes.ok ? await alertSumRes.json() : null;
            const anprSum = anprSumRes.ok ? await anprSumRes.json() : null;
            const camData = await camRes.json().catch(() => cameras);
            
            setMetrics({
                totalCameras: camData.length || 0,
                activeAlerts: alertSum?.active_alerts || 0,
                criticalAlerts: alertSum?.by_severity?.CRITICAL || 0,
                anprTotal: anprSum?.total_reads || 0,
            });
        } catch (e) {
            console.error("Dashboard fetch error", e);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(() => setSnapshotTick(prev => prev + 1), 2000);
        return () => clearInterval(interval);
    }, []);

    // Refresh data on new WS event
    useEffect(() => {
        if (IS_DEMO_MODE) return;
        if (events.length > 0) {
            const latest = events[0];
            if (latest.type === 'NEW_ALERT' || latest.type === 'ANPR_READ') {
                fetchData();
            }
        }
    }, [events]);

    // Demo Mode: Rotating incidents & dynamic metrics override
    useEffect(() => {
        if (!IS_DEMO_MODE) return;
        
        let poolIndex = 0;
        
        // Initial setup
        const updateDemoState = () => {
            const evt = DEMO_INCIDENTS_POOL[poolIndex % DEMO_INCIDENTS_POOL.length];
            const ts = new Date().toISOString();
            
            setAlerts(prev => {
                const newAlerts = [{...evt, created_at: ts}, ...prev];
                return newAlerts.slice(0, 4);
            });
            
            poolIndex++;
        };
        
        updateDemoState();
        const demoInterval = setInterval(updateDemoState, 15000);
        return () => clearInterval(demoInterval);
    }, []);

    // Demo Mode: Metrics sync
    useEffect(() => {
        if (IS_DEMO_MODE) {
            setMetrics({
                totalCameras: DEMO_CAMERAS.length,
                activeAlerts: alerts.length,
                criticalAlerts: alerts.filter(a => a.severity === 'CRITICAL').length,
                anprTotal: DEMO_ANPR_READS.length
            });
        }
    }, [alerts, IS_DEMO_MODE]);

    const PIPELINE_STAGES = [
        { name: "M2 INGEST", active: true },
        { name: "M3 DETECT", active: true },
        { name: "M4 TRACK", active: true },
        { name: "M5 SPATIAL", active: true },
        { name: "M6 EVENTS", active: true },
        { name: "M7 BEHAVIOR", active: true },
        { name: "M8 SCENE", active: true },
        { name: "M9 ANPR", active: true },
        { name: "M10 EVID", active: true },
        { name: "M11 CLIPS", active: true },
        { name: "M12 UI", active: true }
    ];

    return (
        <div className="flex flex-col gap-6 p-6 h-full relative bg-background overflow-hidden">
            {/* Top Metrics Row */}
            <div className="grid grid-cols-4 gap-6 shrink-0">
                <div className="tech-panel p-4 flex flex-col gap-2 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-secondary/5 rounded-bl-full pointer-events-none group-hover:bg-secondary/10 transition-colors"></div>
                    <span className="font-label-caps text-on-surface-variant text-[10px] tracking-widest uppercase">Cameras Active</span>
                    <div className="flex justify-between items-end mt-1">
                        <span className="font-display-lg text-3xl font-light text-on-surface leading-none">{metrics.totalCameras}</span>
                        <span className="material-symbols-outlined text-secondary text-[24px]">videocam</span>
                    </div>
                </div>
                
                <div className={`tech-panel p-4 flex flex-col gap-2 relative overflow-hidden group ${metrics.activeAlerts > 0 ? 'sev-high' : 'sev-low'}`}>
                    <div className={`absolute top-0 right-0 w-16 h-16 ${metrics.activeAlerts > 0 ? 'bg-[#ff9900]/5 group-hover:bg-[#ff9900]/10' : 'bg-primary-dim/5 group-hover:bg-primary-dim/10'} rounded-bl-full pointer-events-none transition-colors`}></div>
                    <span className="font-label-caps text-on-surface-variant text-[10px] tracking-widest uppercase">Active Alerts</span>
                    <div className="flex justify-between items-end mt-1">
                        <span className="font-display-lg text-3xl font-light text-on-surface leading-none">{metrics.activeAlerts}</span>
                        <span className={`material-symbols-outlined text-[24px] ${metrics.activeAlerts > 0 ? 'text-[#ff9900]' : 'text-primary-dim'}`}>emergency</span>
                    </div>
                </div>
                
                <div className={`tech-panel p-4 flex flex-col gap-2 relative overflow-hidden group ${metrics.criticalAlerts > 0 ? 'sev-critical' : 'sev-low'}`}>
                    <div className={`absolute top-0 right-0 w-16 h-16 ${metrics.criticalAlerts > 0 ? 'bg-[#ff3333]/5 group-hover:bg-[#ff3333]/10' : 'bg-primary-dim/5 group-hover:bg-primary-dim/10'} rounded-bl-full pointer-events-none transition-colors`}></div>
                    <span className="font-label-caps text-on-surface-variant text-[10px] tracking-widest uppercase">Critical Alerts</span>
                    <div className="flex justify-between items-end mt-1">
                        <span className="font-display-lg text-3xl font-light text-on-surface leading-none">{metrics.criticalAlerts}</span>
                        <span className={`material-symbols-outlined text-[24px] ${metrics.criticalAlerts > 0 ? 'text-[#ff3333] animate-pulse' : 'text-primary-dim'}`}>warning</span>
                    </div>
                </div>
                
                <div className="tech-panel p-4 flex flex-col gap-2 relative overflow-hidden group border-l-2 border-l-primary">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-primary/5 rounded-bl-full pointer-events-none group-hover:bg-primary/10 transition-colors"></div>
                    <span className="font-label-caps text-on-surface-variant text-[10px] tracking-widest uppercase">ANPR Reads (Total)</span>
                    <div className="flex justify-between items-end mt-1">
                        <span className="font-display-lg text-3xl font-light text-on-surface leading-none">{metrics.anprTotal}</span>
                        <span className="material-symbols-outlined text-primary text-[24px]">directions_car</span>
                    </div>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex gap-6 min-h-0">
                {/* Left: Surveillance Matrix */}
                <div className="flex-[2] flex flex-col tech-panel overflow-hidden relative">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/50 bg-surface-dim backdrop-blur z-10 shrink-0">
                        <div className="flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_5px_rgba(0,240,255,0.5)] animate-pulse"></span>
                            <span className="font-label-caps text-on-surface-variant uppercase tracking-widest text-[11px]">Live Matrix</span>
                        </div>
                        <button onClick={() => navigate('/live')} className="text-primary hover:text-primary-dim font-label-caps text-[10px] uppercase flex items-center gap-1 transition-colors">
                            Full Surveillance <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                        </button>
                    </div>
                    <div className="grid grid-cols-2 grid-rows-2 gap-1 flex-1 bg-surface-container-highest overflow-hidden">
                        {cameras.slice(0, 4).map(cam => (
                            <div key={cam.camera_id} className="bg-background relative group overflow-hidden flex items-center justify-center">
                                {IS_DEMO_MODE ? (
                                    <DemoCameraSnapshot cam={cam} />
                                ) : (
                                    <CameraSnapshot camId={cam.camera_id} tick={snapshotTick} />
                                )}
                                <div className="absolute inset-0 bg-gradient-to-b from-background/90 via-transparent to-background/90 pointer-events-none z-10"></div>
                                <div className="absolute top-2 left-2 flex flex-col gap-1 z-20">
                                    <span className="bg-background/80 backdrop-blur px-2 py-1 font-display font-bold text-[12px] text-primary rounded-sm border border-primary/20 tracking-wider shadow-[0_0_5px_rgba(0,240,255,0.1)] uppercase">
                                        {cam.name || cam.camera_id}
                                    </span>
                                    {(cam.scene_state || IS_DEMO_MODE) && (
                                        <span className="bg-background/80 backdrop-blur px-2 py-0.5 font-label-caps text-[9px] text-on-surface-variant rounded-sm uppercase tracking-widest border border-outline-variant/50 w-fit">
                                            {IS_DEMO_MODE ? 'LIVE' : cam.scene_state}
                                        </span>
                                    )}
                                </div>
                                <div className="absolute bottom-2 left-2 flex gap-1 z-20 font-data-mono text-[9px] tracking-wider">
                                    <span className="bg-background/80 backdrop-blur px-2 py-0.5 rounded-sm text-outline-variant border border-outline-variant/50">FPS: {cam.fps || 30}</span>
                                    <span className="bg-primary/10 backdrop-blur px-2 py-0.5 rounded-sm text-primary border border-primary/30 shadow-[0_0_5px_rgba(0,240,255,0.1)]">TRK: {cam.active_track_count || 0}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Right: Feed Column */}
                <div className="flex-1 flex flex-col gap-6 min-w-[320px]">
                    {/* Active Alerts */}
                    <div className="flex-1 tech-panel flex flex-col overflow-hidden">
                        <div className="px-4 py-3 border-b border-outline-variant/50 bg-surface-dim backdrop-blur flex justify-between items-center shrink-0">
                            <span className="font-label-caps text-on-surface-variant uppercase text-[11px] tracking-widest flex items-center gap-2">
                                <span className="material-symbols-outlined text-[14px]">emergency</span>
                                Active Incidents
                            </span>
                            <span className="badge-critical font-data-mono">{alerts.length}</span>
                        </div>
                        <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3 custom-scrollbar bg-surface-container-lowest/50">
                            {alerts.length === 0 && (
                                <div className="text-center p-6 text-outline-variant text-xs font-data-mono border border-dashed border-outline-variant/30 rounded flex flex-col items-center gap-2 mt-2">
                                    <span className="material-symbols-outlined text-[24px]">verified</span>
                                    NO ACTIVE INCIDENTS
                                </div>
                            )}
                            {alerts.map(a => {
                                const sevClass = a.severity === 'CRITICAL' ? 'sev-critical' : a.severity === 'HIGH' ? 'sev-high' : a.severity === 'MEDIUM' ? 'sev-medium' : 'sev-low';
                                const badgeClass = a.severity === 'CRITICAL' ? 'badge-critical' : a.severity === 'HIGH' ? 'badge-high' : a.severity === 'MEDIUM' ? 'badge-medium' : 'badge-low';
                                
                                return (
                                    <div key={a.alert_id} onClick={() => navigate(`/alerts`)} className={`bg-surface p-3 rounded border border-outline-variant/50 ${sevClass} cursor-pointer hover:bg-surface-variant transition-colors shadow-sm`}>
                                        <div className="flex justify-between items-center mb-2">
                                            <span className={`badge ${badgeClass}`}>{a.severity}</span>
                                            <span className="font-data-mono text-[10px] text-outline-variant">{new Date(a.created_at).toLocaleTimeString()}</span>
                                        </div>
                                        <h4 className="font-body-sm text-[12px] text-on-surface font-medium truncate leading-tight mb-2">{a.title || a.event_type}</h4>
                                        <div className="flex items-center gap-3 font-data-mono text-[10px] text-on-surface-variant">
                                            <div className="flex items-center gap-1"><span className="material-symbols-outlined text-[12px]">videocam</span> <span className="text-primary">{a.camera_id}</span></div>
                                            {a.track_id && <div className="flex items-center gap-1"><span className="material-symbols-outlined text-[12px]">my_location</span> <span className="text-primary">TRK-{a.track_id}</span></div>}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Recent ANPR */}
                    <div className="h-[220px] tech-panel flex flex-col overflow-hidden shrink-0">
                        <div className="px-4 py-3 border-b border-outline-variant/50 bg-surface-dim backdrop-blur flex justify-between items-center shrink-0">
                            <span className="font-label-caps text-on-surface-variant uppercase text-[11px] tracking-widest flex items-center gap-2">
                                <span className="material-symbols-outlined text-[14px]">directions_car</span>
                                Intelligence: ANPR
                            </span>
                        </div>
                        <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2 custom-scrollbar bg-surface-container-lowest/50">
                            {anprReads.length === 0 && (
                                <div className="text-center p-4 text-outline-variant text-xs font-data-mono flex flex-col items-center gap-2 mt-2">
                                    NO RECENT PLATES
                                </div>
                            )}
                            {anprReads.map(r => (
                                <div key={r.event_id} onClick={() => navigate('/anpr')} className="bg-surface px-3 py-2 rounded border border-outline-variant/30 border-l-2 border-l-primary cursor-pointer hover:bg-surface-variant transition-colors flex justify-between items-center">
                                    <div className="flex flex-col gap-1">
                                        <span className="font-data-mono text-[13px] font-bold text-on-surface tracking-widest">{r.plate_text}</span>
                                        <span className="font-data-mono text-[9px] text-outline-variant uppercase">CAM: {r.camera_id}</span>
                                    </div>
                                    <div className="flex flex-col items-end gap-1">
                                        <span className="font-data-mono text-[9px] text-outline-variant">{new Date(r.timestamp).toLocaleTimeString()}</span>
                                        <span className="font-data-mono text-[9px] text-primary bg-primary/10 px-1 rounded uppercase border border-primary/20">{r.vehicle_class}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Pipeline Telemetry */}
            <div className="h-10 tech-panel flex items-center px-6 shrink-0 relative overflow-hidden bg-surface-dim">
                <div className="absolute left-6 right-6 h-px bg-outline-variant/30 top-1/2 -translate-y-1/2 z-0"></div>
                <div className="w-full flex justify-between items-center z-10 font-data-mono text-[10px]">
                    {PIPELINE_STAGES.map((stage, i) => (
                        <div key={i} className="flex flex-col items-center gap-1.5 relative bg-surface-dim px-3">
                            <span className="text-outline-variant uppercase text-[9px] tracking-widest">{stage.name}</span>
                            <div className={`w-2 h-2 rounded-full ${stage.active ? 'bg-secondary shadow-[0_0_8px_rgba(0,255,166,0.8)]' : 'bg-outline-variant'}`}></div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
