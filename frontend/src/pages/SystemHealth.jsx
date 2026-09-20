import { useState, useEffect } from 'react';
import { systemApi } from '../api/client';

export default function SystemHealth() {
    const [status, setStatus] = useState(null);
    const [metrics, setMetrics] = useState(null);

    const fetchData = async () => {
        try {
            const [statRes, metRes] = await Promise.all([
                systemApi.status(),
                systemApi.metrics()
            ]);
            
            if (statRes.ok) setStatus(await statRes.json());
            if (metRes.ok) setMetrics(await metRes.json());
        } catch (e) {
            console.error("fetch system health failed", e);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-6 gap-6 overflow-auto custom-scrollbar">
            <div className="flex justify-between items-center shrink-0 tech-panel p-6 bg-surface shadow-md">
                <h1 className="font-display-lg text-2xl font-light text-on-surface flex items-center gap-3 tracking-wide">
                    <span className="material-symbols-outlined text-primary text-[28px]">ecg</span> System Health
                </h1>
            </div>

            <div className="grid grid-cols-3 gap-6">
                {/* Resources */}
                <div className="col-span-2 tech-panel bg-surface p-6 flex flex-col gap-6 shadow-md border-t-2 border-t-primary">
                    <h2 className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest border-b border-outline-variant/30 pb-3 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-primary rounded-full"></span>
                        Hardware Utilization
                    </h2>
                    {metrics ? (
                        <div className="grid grid-cols-2 gap-8">
                            <div className="flex flex-col gap-4">
                                <div className="flex flex-col gap-2">
                                    <div className="flex justify-between font-data-mono text-[11px] uppercase tracking-widest">
                                        <span className="text-on-surface-variant">CPU Usage</span>
                                        <span className="text-primary font-bold">{metrics.cpu_percent}%</span>
                                    </div>
                                    <div className="h-2.5 bg-surface-dim border border-outline-variant/30 rounded overflow-hidden">
                                        <div className="h-full bg-primary shadow-[0_0_10px_rgba(0,240,255,0.5)] transition-all duration-500" style={{ width: `${metrics.cpu_percent}%` }}></div>
                                    </div>
                                </div>
                                
                                <div className="flex flex-col gap-2 mt-2">
                                    <div className="flex justify-between font-data-mono text-[11px] uppercase tracking-widest">
                                        <span className="text-on-surface-variant">System RAM</span>
                                        <span className="text-primary font-bold">{metrics.ram_percent}%</span>
                                    </div>
                                    <div className="h-2.5 bg-surface-dim border border-outline-variant/30 rounded overflow-hidden">
                                        <div className="h-full bg-primary shadow-[0_0_10px_rgba(0,240,255,0.5)] transition-all duration-500" style={{ width: `${metrics.ram_percent}%` }}></div>
                                    </div>
                                    <div className="text-right font-data-mono text-[10px] text-outline-variant tracking-widest">
                                        {metrics.ram_used_gb.toFixed(1)} GB / {metrics.ram_total_gb.toFixed(1)} GB
                                    </div>
                                </div>
                            </div>
                            
                            <div className="flex flex-col gap-4">
                                <h3 className="font-label-caps text-[11px] text-secondary tracking-widest uppercase">GPU Status</h3>
                                {metrics.gpus && metrics.gpus.length > 0 ? (
                                    metrics.gpus.map((gpu, i) => (
                                        <div key={i} className="flex flex-col gap-2 mb-2 p-3 bg-surface-dim border border-outline-variant/30 rounded">
                                            <div className="flex justify-between font-data-mono text-[11px] uppercase tracking-widest">
                                                <span className="text-on-surface truncate pr-2 font-bold">{gpu.name}</span>
                                                <span className="text-secondary font-bold">{gpu.load_percent}%</span>
                                            </div>
                                            <div className="h-1.5 bg-background rounded overflow-hidden">
                                                <div className="h-full bg-secondary shadow-[0_0_10px_rgba(0,255,166,0.5)] transition-all duration-500" style={{ width: `${gpu.load_percent}%` }}></div>
                                            </div>
                                            <div className="flex justify-between font-data-mono text-[10px] text-outline-variant tracking-widest mt-1">
                                                <span>Temp: {gpu.temperature_c}°C</span>
                                                <span>Mem: {(gpu.memory_used_mb/1024).toFixed(1)}GB / {(gpu.memory_total_mb/1024).toFixed(1)}GB</span>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-outline-variant/50 font-data-mono text-[11px] p-4 border border-outline-variant/30 border-dashed rounded text-center tracking-widest uppercase">No GPUs detected (CPU Fallback)</div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="text-primary font-data-mono text-[11px] animate-pulse tracking-widest uppercase">Loading metrics...</div>
                    )}
                </div>

                {/* Modules */}
                {/* Modules */}
                <div className="tech-panel bg-surface p-6 flex flex-col gap-4 shadow-md border-t-2 border-t-secondary">
                    <h2 className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest border-b border-outline-variant/30 pb-3 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-secondary rounded-full"></span>
                        Pipeline Modules
                    </h2>
                    {status && status.modules ? (
                        <div className="flex flex-col gap-3 font-data-mono text-[11px]">
                            {Object.entries(status.modules).map(([mod, state]) => (
                                <div key={mod} className="flex justify-between items-center bg-surface-dim p-3 rounded border border-outline-variant/30">
                                    <span className="text-on-surface uppercase tracking-widest font-bold">{mod.replace('_', ' ')}</span>
                                    <span className={`badge ${state === 'ONLINE' ? 'badge-secondary' : state === 'DEGRADED' ? 'bg-[#ff9900]/10 text-[#ff9900] border border-[#ff9900]/30' : 'badge-neutral'}`}>
                                        {state}
                                    </span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-primary font-data-mono text-[11px] animate-pulse tracking-widest uppercase">Loading status...</div>
                    )}
                </div>
            </div>
            
            {/* System Info */}
            <div className="tech-panel bg-surface p-6 flex flex-col gap-6 shadow-md border-t-2 border-t-[#b366ff]">
                <h2 className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest border-b border-outline-variant/30 pb-3 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#b366ff] rounded-full"></span>
                    Platform Details
                </h2>
                {status && metrics && (
                    <div className="grid grid-cols-4 gap-6 font-data-mono text-[11px] bg-surface-dim p-6 rounded border border-outline-variant/30">
                        <div className="flex flex-col gap-2">
                            <span className="text-outline-variant tracking-widest uppercase">Version</span>
                            <span className="text-on-surface font-bold tracking-widest">{status.version}</span>
                        </div>
                        <div className="flex flex-col gap-2">
                            <span className="text-outline-variant tracking-widest uppercase">Milestone</span>
                            <span className="text-primary font-bold tracking-widest">M{status.milestone}</span>
                        </div>
                        <div className="flex flex-col gap-2">
                            <span className="text-outline-variant tracking-widest uppercase">Uptime</span>
                            <span className="text-on-surface font-bold tracking-widest">{(metrics.uptime_seconds / 3600).toFixed(1)} Hours</span>
                        </div>
                        <div className="flex flex-col gap-2">
                            <span className="text-outline-variant tracking-widest uppercase">Host</span>
                            <span className="text-on-surface font-bold tracking-widest">ibvap-edge-node-01</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
