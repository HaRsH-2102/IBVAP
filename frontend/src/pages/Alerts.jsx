import { useState, useEffect } from 'react';
import { alertApi } from '../api/client';
import { useNavigate } from 'react-router-dom';
import { useWs } from '../api/ws';

export default function Alerts() {
    const [alerts, setAlerts] = useState([]);
    const [summary, setSummary] = useState(null);
    const navigate = useNavigate();
    const { events } = useWs();

    const formatTimestamp = (ts) => {
        if (!ts) return 'Time unavailable';
        let d = new Date(ts);
        if (isNaN(d.getTime()) && typeof ts === 'string') {
            d = new Date(ts.replace(/(\.\d{3})\d+/, '$1'));
        }
        return isNaN(d.getTime()) ? 'Time unavailable' : d.toLocaleTimeString();
    };

    const fetchData = async () => {
        try {
            const [listRes, sumRes] = await Promise.all([
                alertApi.listActive(),
                alertApi.summary()
            ]);
            
            if (listRes.ok) {
                const data = await listRes.json();
                setAlerts(data.filter(a => a.status === 'OPEN' || a.status === 'ACKNOWLEDGED'));
            }
            if (sumRes.ok) setSummary(await sumRes.json());
        } catch (e) {
            console.error("fetch alerts failed", e);
        }
    };

    useEffect(() => { fetchData(); }, []);

    // Real-time incremental capture
    useEffect(() => {
        if (events.length > 0) {
            const latestEvent = events[0];
            if (latestEvent.type === 'NEW_ALERT' && latestEvent.alert) {
                const incoming = latestEvent.alert;
                setAlerts(prev => {
                    // Check if exists
                    const exists = prev.find(a => a.alert_id === incoming.alert_id);
                    if (exists) {
                        // Update status if it changed, otherwise return same
                        if (exists.status !== incoming.status) {
                            return prev.map(a => a.alert_id === incoming.alert_id ? { ...a, status: incoming.status } : a);
                        }
                        return prev;
                    } else {
                        // Fetch the full alert details from API to get description, evidence etc.
                        // We do it asynchronously and don't block the render
                        alertApi.get(incoming.alert_id).then(res => {
                            if (res.ok) {
                                res.json().then(fullAlert => {
                                    setAlerts(current => {
                                        // verify it's still not there and not resolved
                                        if (current.find(a => a.alert_id === fullAlert.alert_id)) return current;
                                        if (fullAlert.status === 'RESOLVED') return current;
                                        return [fullAlert, ...current];
                                    });
                                });
                            }
                        });
                        // Optimistically insert minimal version
                        return [incoming, ...prev];
                    }
                });
            }
        }
    }, [events]);

    const handleAck = async (e, alertId) => {
        e.stopPropagation();
        try {
            const res = await alertApi.acknowledge(alertId, 'operator-01');
            if (res.ok) {
                const data = await res.json();
                setAlerts(prev => prev.map(a => a.alert_id === alertId ? { ...a, status: data.status } : a));
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleResolve = async (e, alertId) => {
        e.stopPropagation();
        try {
            const res = await alertApi.resolve(alertId, 'operator-01', 'Resolved via active incidents page');
            if (res.ok) {
                setAlerts(prev => prev.filter(a => a.alert_id !== alertId)); // Remove from active
            }
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-6 gap-6">
            <div className="flex justify-between items-center shrink-0">
                <div className="flex items-center gap-4">
                    <h1 className="font-display-lg text-2xl font-light text-on-surface tracking-wide flex items-center gap-3">
                        <span className="material-symbols-outlined text-[#ff9900] text-[28px]">emergency</span>
                        Active Incidents
                    </h1>
                </div>
                <div className="flex gap-4 items-center">
                    {/* WebSocket Connection Status */}
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-dim rounded border border-outline-variant/30">
                        <span className={`w-2 h-2 rounded-full shadow-[0_0_5px_currentColor] ${events.length >= 0 ? 'bg-secondary text-secondary animate-pulse' : 'bg-error text-error'}`}></span>
                        <span className="font-data-mono text-[10px] uppercase tracking-widest text-outline-variant">
                            {events.length >= 0 ? 'LIVE TOC' : 'DISCONNECTED'}
                        </span>
                    </div>
                    <button onClick={fetchData} className="text-on-surface-variant hover:text-on-surface transition-colors flex items-center justify-center p-2 rounded border border-outline-variant/30 bg-surface hover:bg-surface-variant">
                        <span className="material-symbols-outlined text-[18px]">refresh</span>
                    </button>
                </div>
            </div>

            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-6 shrink-0">
                    <div className="tech-panel p-4 flex flex-col gap-2 bg-surface">
                        <span className="font-label-caps text-outline-variant text-[10px] uppercase tracking-widest">Active Alerts</span>
                        <span className="font-display-lg text-3xl font-light text-on-surface leading-none">{summary.active_alerts}</span>
                    </div>
                    <div className="tech-panel p-4 flex flex-col gap-2 sev-critical group relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-[#ff3333]/5 rounded-bl-full pointer-events-none group-hover:bg-[#ff3333]/10 transition-colors"></div>
                        <span className="font-label-caps text-outline-variant text-[10px] uppercase tracking-widest">Critical</span>
                        <span className="font-display-lg text-3xl font-light text-[#ff3333] leading-none">{summary.by_severity?.CRITICAL || 0}</span>
                    </div>
                    <div className="tech-panel p-4 flex flex-col gap-2 sev-high group relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-[#ff9900]/5 rounded-bl-full pointer-events-none group-hover:bg-[#ff9900]/10 transition-colors"></div>
                        <span className="font-label-caps text-outline-variant text-[10px] uppercase tracking-widest">High</span>
                        <span className="font-display-lg text-3xl font-light text-[#ff9900] leading-none">{summary.by_severity?.HIGH || 0}</span>
                    </div>
                    <div className="tech-panel p-4 flex flex-col gap-2 sev-medium group relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-[#facc15]/5 rounded-bl-full pointer-events-none group-hover:bg-[#facc15]/10 transition-colors"></div>
                        <span className="font-label-caps text-outline-variant text-[10px] uppercase tracking-widest">Medium</span>
                        <span className="font-display-lg text-3xl font-light text-[#facc15] leading-none">{summary.by_severity?.MEDIUM || 0}</span>
                    </div>
                    <div className="tech-panel p-4 flex flex-col gap-2 sev-low group relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-[#00f0ff]/5 rounded-bl-full pointer-events-none group-hover:bg-[#00f0ff]/10 transition-colors"></div>
                        <span className="font-label-caps text-outline-variant text-[10px] uppercase tracking-widest">Low</span>
                        <span className="font-display-lg text-3xl font-light text-[#00f0ff] leading-none">{summary.by_severity?.LOW || 0}</span>
                    </div>
                </div>
            )}

            <div className="flex-1 tech-panel overflow-hidden flex flex-col min-h-0">
                <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim flex justify-between items-center shrink-0">
                    <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest">Incident Queue</span>
                    <span className="badge badge-neutral">{alerts.length} PENDING</span>
                </div>
                <div className="flex-1 overflow-auto bg-background p-6 custom-scrollbar">
                    {alerts.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-outline-variant gap-4 font-data-mono">
                            <span className="material-symbols-outlined text-[64px] opacity-20">shield_with_heart</span>
                            <p className="text-sm tracking-widest uppercase">No active incidents</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                            {alerts.map(a => {
                                const isCritical = a.severity === 'CRITICAL';
                                const isHigh = a.severity === 'HIGH';
                                const isMedium = a.severity === 'MEDIUM';
                                
                                const sevClass = isCritical ? 'sev-critical' : isHigh ? 'sev-high' : isMedium ? 'sev-medium' : 'sev-low';
                                const badgeClass = isCritical ? 'badge-critical' : isHigh ? 'badge-high' : isMedium ? 'badge-medium' : 'badge-low';

                                return (
                                    <div 
                                        key={a.alert_id} 
                                        className={`bg-surface p-5 flex flex-col gap-5 border border-outline-variant/30 hover:bg-surface-variant hover:border-outline-variant transition-colors group shadow-md ${sevClass}`}
                                    >
                                        <div className="flex justify-between items-start gap-2">
                                            <div className="flex items-center gap-3 flex-wrap">
                                                <span className={`badge ${badgeClass} text-[10px] shadow-[0_0_10px_currentColor]`}>{a.severity}</span>
                                                <h4 className="font-body-base text-on-surface font-semibold uppercase tracking-wide">
                                                    {a.title || a.event_type.replace('_', ' ')}
                                                </h4>
                                            </div>
                                            <span className={`font-label-caps text-[9px] uppercase tracking-widest px-2 py-1 rounded border ${a.status === 'OPEN' ? 'border-[#ff3333] text-[#ff3333]' : 'border-secondary text-secondary'}`}>
                                                {a.status}
                                            </span>
                                        </div>

                                        <div className="flex flex-col gap-2 font-data-mono text-[12px] text-on-surface-variant bg-surface-dim p-4 rounded border border-outline-variant/30">
                                            <div className="flex justify-between items-center">
                                                <span className="text-outline-variant uppercase text-[10px] tracking-widest">Camera</span>
                                                <span className="text-on-surface font-bold tracking-widest">{a.camera_id}</span>
                                            </div>
                                            <div className="w-full h-px bg-outline-variant/20"></div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-outline-variant uppercase text-[10px] tracking-widest">Track ID</span>
                                                <span className="text-primary tracking-widest">{a.track_id}</span>
                                            </div>
                                            <div className="w-full h-px bg-outline-variant/20"></div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-outline-variant uppercase text-[10px] tracking-widest">Time</span>
                                                <span className="text-on-surface tracking-widest">{formatTimestamp(a.created_at)}</span>
                                            </div>
                                        </div>

                                        {a.description && (
                                            <p className="text-sm text-on-surface-variant font-body-sm line-clamp-2">
                                                {a.description}
                                            </p>
                                        )}

                                        {a.security_event_ids && a.security_event_ids.length > 0 && (
                                            <div className="flex items-center gap-2 text-secondary text-[11px] font-label-caps tracking-widest bg-secondary/10 border border-secondary/20 px-3 py-1.5 rounded w-fit">
                                                <span className="material-symbols-outlined text-[14px]">image</span>
                                                EVIDENCE ATTACHED
                                            </div>
                                        )}

                                        <div className="flex items-center justify-between gap-3 pt-4 border-t border-outline-variant/30 mt-auto flex-wrap">
                                            <button 
                                                onClick={() => navigate(`/alerts/${a.alert_id}`)}
                                                className="px-4 py-2 bg-surface-variant border border-outline-variant/50 text-on-surface-variant hover:text-on-surface font-label-caps text-[10px] rounded transition-colors uppercase tracking-widest shadow-sm">
                                                View Details
                                            </button>
                                            
                                            <div className="flex gap-3">
                                                {a.status === 'OPEN' && (
                                                    <button 
                                                        onClick={(e) => handleAck(e, a.alert_id)}
                                                        className="px-4 py-2 border border-primary/50 text-primary hover:bg-primary/10 hover:shadow-[0_0_10px_rgba(0,240,255,0.1)] font-label-caps text-[10px] rounded transition-all uppercase tracking-widest">
                                                        Acknowledge
                                                    </button>
                                                )}
                                                <button 
                                                    onClick={(e) => handleResolve(e, a.alert_id)}
                                                    className="px-4 py-2 border border-secondary/50 text-secondary hover:bg-secondary/10 hover:shadow-[0_0_10px_rgba(0,255,166,0.1)] font-label-caps text-[10px] rounded transition-all uppercase tracking-widest">
                                                    Resolve
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
