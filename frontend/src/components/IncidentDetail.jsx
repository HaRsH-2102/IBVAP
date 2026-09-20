import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

export default function IncidentDetail() {
    const { id: alertId } = useParams();
    const navigate = useNavigate();
    const [alert, setAlert] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchDetail = async () => {
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/v1/alerts/${alertId}`);
            if (res.ok) {
                const data = await res.json();
                setAlert(data);
            }
        } catch (e) {
            console.error("fetchDetail error", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDetail();
    }, [alertId]);

    const handleAck = async () => {
        await fetch(`http://127.0.0.1:8000/api/v1/alerts/${alertId}/ack`, { method: 'PATCH' });
        fetchDetail();
    };

    const handleResolve = async () => {
        await fetch(`http://127.0.0.1:8000/api/v1/alerts/${alertId}/resolve`, { method: 'PATCH' });
        fetchDetail();
    };

    if (loading) return <div className="h-full flex items-center justify-center text-outline-variant font-data-mono bg-background">Loading incident data...</div>;
    if (!alert) return <div className="h-full flex items-center justify-center text-error font-data-mono bg-background">Incident not found or restricted</div>;

    const isCritical = alert.severity === 'CRITICAL';
    const isHigh = alert.severity === 'HIGH';
    const isMedium = alert.severity === 'MEDIUM';
    const sevClass = isCritical ? 'sev-critical' : isHigh ? 'sev-high' : isMedium ? 'sev-medium' : 'sev-low';
    const badgeClass = isCritical ? 'badge-critical' : isHigh ? 'badge-high' : isMedium ? 'badge-medium' : 'badge-low';

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-6 gap-6">
            {/* Header Section */}
            <div className={`tech-panel p-6 flex justify-between items-center shrink-0 border-l-4 ${sevClass} bg-surface`}>
                <div className="flex flex-col gap-2">
                    <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-outline-variant hover:text-on-surface text-[10px] font-label-caps tracking-widest uppercase mb-1 transition-colors w-fit">
                        <span className="material-symbols-outlined text-[14px]">arrow_back</span> Return to Queue
                    </button>
                    <div className="flex items-center gap-3">
                        <span className={`badge ${badgeClass} text-[10px] shadow-[0_0_10px_currentColor]`}>{alert.severity}</span>
                        <span className={`font-label-caps text-[10px] uppercase tracking-widest px-2 py-1 rounded border ${alert.status === 'OPEN' ? 'border-[#ff3333] text-[#ff3333]' : 'border-secondary text-secondary'}`}>
                            {alert.status}
                        </span>
                        <span className="font-data-mono text-[10px] text-outline-variant ml-2">{alert.alert_id}</span>
                    </div>
                    <h1 className="font-display-lg text-2xl font-light text-on-surface tracking-wide mt-1">{alert.title || alert.event_type}</h1>
                </div>
                <div className="flex gap-4 items-center">
                    <button 
                        onClick={handleAck}
                        disabled={alert.status !== 'OPEN'}
                        className="px-6 py-2.5 bg-surface-dim border border-primary/50 text-primary hover:bg-primary/10 hover:shadow-[0_0_10px_rgba(0,240,255,0.1)] rounded font-label-caps tracking-widest text-[11px] disabled:opacity-50 disabled:hover:shadow-none transition-all uppercase">
                        Acknowledge
                    </button>
                    <button 
                        onClick={handleResolve}
                        disabled={alert.status === 'RESOLVED'}
                        className="px-6 py-2.5 bg-surface-dim border border-secondary/50 text-secondary hover:bg-secondary/10 hover:shadow-[0_0_10px_rgba(0,255,166,0.1)] rounded font-label-caps tracking-widest text-[11px] disabled:opacity-50 disabled:hover:shadow-none transition-all uppercase">
                        Resolve
                    </button>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">
                {/* Left: Evidence Viewer */}
                <div className="col-span-7 tech-panel flex flex-col overflow-hidden bg-surface">
                    <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim flex justify-between items-center">
                        <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest flex items-center gap-2">
                            <span className="material-symbols-outlined text-[16px]">image</span> Key Evidence
                        </span>
                        <span className={`badge ${alert.evidence ? 'badge-secondary' : 'badge-neutral'}`}>
                            {alert.evidence ? 'AVAILABLE' : 'UNAVAILABLE'}
                        </span>
                    </div>
                    <div className="flex-1 relative bg-black flex items-center justify-center">
                        {alert.evidence ? (
                            <img 
                                className="w-full h-full object-contain" 
                                src={`http://127.0.0.1:8000/api/v1/events/${alert.evidence.security_event_id}/evidence`}
                                onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'block'; }}
                                alt="Evidence"
                            />
                        ) : null}
                        <div style={{display: alert.evidence ? 'none' : 'block'}} className="text-outline-variant font-data-mono text-[12px] tracking-widest">
                            EVIDENCE UNAVAILABLE
                        </div>
                    </div>
                    <div className="p-4 bg-surface-dim border-t border-outline-variant/50 grid grid-cols-3 gap-6 shrink-0">
                        <div className="flex flex-col gap-1">
                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Camera ID</span>
                            <span className="text-on-surface font-data-mono text-[12px] truncate">{alert.camera_id}</span>
                        </div>
                        <div className="flex flex-col gap-1">
                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Timestamp</span>
                            <span className="text-on-surface font-data-mono text-[12px]">{new Date(alert.created_at).toLocaleTimeString()}</span>
                        </div>
                        <div className="flex flex-col gap-1">
                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Track ID</span>
                            <span className="text-primary font-data-mono text-[12px] truncate">{alert.track_id}</span>
                        </div>
                    </div>
                </div>

                {/* Right: Clip Player */}
                <div className="col-span-5 tech-panel flex flex-col overflow-hidden bg-surface">
                    <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim flex justify-between items-center shrink-0">
                        <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest flex items-center gap-2">
                            <span className="material-symbols-outlined text-[16px]">movie</span> Incident Clip
                        </span>
                        <span className="badge badge-neutral">
                            {alert.clip ? alert.clip.status : 'UNAVAILABLE'}
                        </span>
                    </div>
                    <div className="flex-1 bg-black relative flex items-center justify-center">
                        <div className="w-full h-full bg-[#0c0e12] relative flex items-center justify-center">
                            {alert.clip ? (
                                <video 
                                    src={`http://127.0.0.1:8000/api/v1/clips/${alert.clip.clip_id}/video`}
                                    controls
                                    className="w-full h-full object-contain"
                                    poster={`http://127.0.0.1:8000/api/v1/clips/${alert.clip.clip_id}/thumbnail`}
                                />
                            ) : (
                                <div className="absolute inset-0 flex flex-col items-center justify-center text-outline-variant gap-4">
                                    <span className="material-symbols-outlined text-[48px] opacity-20">videocam_off</span>
                                    <span className="font-data-mono text-[10px] uppercase tracking-widest">Clip Not Available</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom: Vertical Event Timeline */}
            <div className="tech-panel p-6 shrink-0 bg-surface flex flex-col gap-6">
                <span className="font-label-caps text-outline-variant uppercase text-[11px] tracking-widest">Pipeline Event Trace</span>
                <div className="flex justify-between items-start relative px-12">
                    <div className="absolute top-[18px] left-16 right-16 h-px bg-outline-variant/30 z-0"></div>
                    
                    <div className="flex flex-col items-center gap-3 relative z-10 w-24">
                        <div className="w-10 h-10 rounded-full bg-surface-dim border border-outline-variant/50 flex items-center justify-center text-on-surface-variant shadow-sm">
                            <span className="material-symbols-outlined text-[18px]">radar</span>
                        </div>
                        <span className="font-data-mono text-[10px] text-center text-on-surface-variant uppercase tracking-widest leading-relaxed">Track<br/>Detected</span>
                    </div>
                    
                    <div className="flex flex-col items-center gap-3 relative z-10 w-24">
                        <div className="w-10 h-10 rounded-full bg-surface-dim border border-outline-variant/50 flex items-center justify-center text-on-surface-variant shadow-sm">
                            <span className="material-symbols-outlined text-[18px]">location_searching</span>
                        </div>
                        <span className="font-data-mono text-[10px] text-center text-on-surface-variant uppercase tracking-widest leading-relaxed">Spatial<br/>Event</span>
                    </div>
                    
                    <div className="flex flex-col items-center gap-3 relative z-10 w-24">
                        <div className={`w-10 h-10 rounded-full bg-[#ff3333]/10 border border-[#ff3333]/50 flex items-center justify-center text-[#ff3333] shadow-[0_0_10px_rgba(255,51,51,0.2)]`}>
                            <span className="material-symbols-outlined text-[18px]">warning</span>
                        </div>
                        <span className="font-data-mono text-[10px] text-center text-[#ff3333] uppercase tracking-widest leading-relaxed">Alert<br/>Created</span>
                    </div>

                    <div className={`flex flex-col items-center gap-3 relative z-10 w-24 transition-opacity ${alert.evidence ? '' : 'opacity-30'}`}>
                        <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/50 flex items-center justify-center text-primary shadow-[0_0_10px_rgba(0,240,255,0.2)]">
                            <span className="material-symbols-outlined text-[18px]">image</span>
                        </div>
                        <span className="font-data-mono text-[10px] text-center text-primary uppercase tracking-widest leading-relaxed">Evidence<br/>Saved</span>
                    </div>

                    <div className={`flex flex-col items-center gap-3 relative z-10 w-24 transition-opacity ${alert.clip ? '' : 'opacity-30'}`}>
                        <div className="w-10 h-10 rounded-full bg-secondary/10 border border-secondary/50 flex items-center justify-center text-secondary shadow-[0_0_10px_rgba(0,255,166,0.2)]">
                            <span className="material-symbols-outlined text-[18px]">movie</span>
                        </div>
                        <span className="font-data-mono text-[10px] text-center text-secondary uppercase tracking-widest leading-relaxed">Clip<br/>Generated</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
