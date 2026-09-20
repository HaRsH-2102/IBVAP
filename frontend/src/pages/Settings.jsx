import { useState, useEffect } from 'react';
import { systemApi } from '../api/client';

export default function Settings() {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const res = await systemApi.status();
                if (res.ok) {
                    const data = await res.json();
                    setConfig(data.configuration);
                }
            } catch (e) {
                console.error("Failed to fetch settings", e);
            } finally {
                setLoading(false);
            }
        };
        fetchConfig();
    }, []);

    const ConfigRow = ({ label, value, status, description }) => (
        <div className="flex justify-between items-start py-4 border-b border-outline-variant/30 last:border-0 group hover:bg-surface-variant/30 px-2 -mx-2 rounded transition-colors">
            <div className="flex flex-col gap-1 max-w-[70%]">
                <span className="font-label-caps text-[11px] text-on-surface uppercase tracking-widest">{label}</span>
                <span className="text-[12px] text-on-surface-variant leading-relaxed">{description}</span>
            </div>
            <div className="flex flex-col items-end gap-2 text-right">
                <span className="font-data-mono text-[14px] text-primary bg-primary/5 px-3 py-1 rounded shadow-[0_0_5px_rgba(0,240,255,0.05)] border border-primary/20">
                    {Array.isArray(value) ? value.join(', ') : value?.toString() || 'N/A'}
                </span>
                <span className={`text-[9px] font-label-caps tracking-widest px-2 py-0.5 rounded border uppercase ${
                    status === 'LIVE' ? 'bg-secondary/10 text-secondary border-secondary/30' : 'bg-[#ff9900]/10 text-[#ff9900] border-[#ff9900]/30'
                }`}>
                    {status}
                </span>
            </div>
        </div>
    );

    if (loading) return <div className="p-6 text-on-surface-variant font-data-mono text-sm">Loading Configuration...</div>;
    if (!config) return <div className="p-6 text-[#ff3333] font-data-mono text-sm">Failed to load configuration.</div>;

    return (
        <div className="flex flex-col h-full bg-background overflow-hidden relative">
            <div className="flex justify-between items-center shrink-0 p-6 border-b border-outline-variant/50 bg-surface-dim z-10">
                <h1 className="font-headline-md text-xl font-bold text-on-surface flex items-center gap-3">
                    <span className="material-symbols-outlined text-primary text-[24px]">tune</span> Platform Settings
                </h1>
                <span className="badge badge-neutral bg-surface-variant border-outline-variant">READ ONLY - DEMO</span>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar pb-24">
                <div className="max-w-4xl mx-auto flex flex-col gap-8">
                    
                    <section className="tech-panel p-6 flex flex-col">
                        <div className="flex items-center gap-2 mb-4 border-b border-outline-variant/30 pb-3">
                            <span className="material-symbols-outlined text-primary text-[18px]">search</span>
                            <h2 className="font-label-caps text-[13px] text-on-surface uppercase tracking-widest">Detection (M3)</h2>
                        </div>
                        <ConfigRow 
                            label="Detector Confidence Threshold" 
                            value={config.detector_confidence_threshold} 
                            status="LIVE" 
                            description="Minimum AI confidence required for an object to be sent to tracking." 
                        />
                        <ConfigRow 
                            label="Enabled Classes" 
                            value={config.detector_enabled_classes} 
                            status="LIVE" 
                            description="Semantic classes preserved from the raw AI detector." 
                        />
                        <ConfigRow 
                            label="Inference Resolution" 
                            value={config.detector_inference_size} 
                            status="RESTART REQUIRED" 
                            description="Input image size sent to the model (e.g., 640x640)." 
                        />
                    </section>

                    <section className="tech-panel p-6 flex flex-col">
                        <div className="flex items-center gap-2 mb-4 border-b border-outline-variant/30 pb-3">
                            <span className="material-symbols-outlined text-primary text-[18px]">my_location</span>
                            <h2 className="font-label-caps text-[13px] text-on-surface uppercase tracking-widest">Tracking (M4) & General</h2>
                        </div>
                        <ConfigRow 
                            label="System Confidence Threshold" 
                            value={config.default_confidence_threshold} 
                            status="LIVE" 
                            description="Global fallback confidence threshold for tracked entities." 
                        />
                    </section>

                    <section className="tech-panel p-6 flex flex-col">
                        <div className="flex items-center gap-2 mb-4 border-b border-outline-variant/30 pb-3">
                            <span className="material-symbols-outlined text-primary text-[18px]">psychology</span>
                            <h2 className="font-label-caps text-[13px] text-on-surface uppercase tracking-widest">Behavioral Intelligence (M7)</h2>
                        </div>
                        <ConfigRow 
                            label="Loitering Threshold (Seconds)" 
                            value={config.loitering_threshold_seconds} 
                            status="LIVE" 
                            description="Minimum continuous dwell time to trigger a loitering incident." 
                        />
                        <ConfigRow 
                            label="Night Movement Start Hour" 
                            value={config.night_start_hour} 
                            status="LIVE" 
                            description="Hour (0-23) when night-movement behavioral rules engage." 
                        />
                        <ConfigRow 
                            label="Night Movement End Hour" 
                            value={config.night_end_hour} 
                            status="LIVE" 
                            description="Hour (0-23) when night-movement behavioral rules disengage." 
                        />
                    </section>

                    <section className="tech-panel p-6 flex flex-col">
                        <div className="flex items-center gap-2 mb-4 border-b border-outline-variant/30 pb-3">
                            <span className="material-symbols-outlined text-primary text-[18px]">directions_car</span>
                            <h2 className="font-label-caps text-[13px] text-on-surface uppercase tracking-widest">Intelligence: ANPR (M9)</h2>
                        </div>
                        <ConfigRow 
                            label="ANPR Engine Enabled" 
                            value={config.anpr_enabled} 
                            status="RESTART REQUIRED" 
                            description="Master toggle for the asynchronous license plate recognition pipeline." 
                        />
                        <ConfigRow 
                            label="Plate Detector Confidence" 
                            value={config.anpr_detector_confidence} 
                            status="LIVE" 
                            description="Minimum confidence to extract a license plate bounding box." 
                        />
                        <ConfigRow 
                            label="Temporal Consensus Threshold" 
                            value={config.anpr_consensus_threshold} 
                            status="LIVE" 
                            description="Minimum identical consecutive plate reads required to trigger an event." 
                        />
                    </section>

                    <section className="tech-panel p-6 flex flex-col">
                        <div className="flex items-center gap-2 mb-4 border-b border-outline-variant/30 pb-3">
                            <span className="material-symbols-outlined text-primary text-[18px]">memory</span>
                            <h2 className="font-label-caps text-[13px] text-on-surface uppercase tracking-widest">Video & System (M2)</h2>
                        </div>
                        <ConfigRow 
                            label="Processing FPS Limit" 
                            value={config.processing_fps_limit} 
                            status="RESTART REQUIRED" 
                            description="Maximum pipeline ingestion rate per camera." 
                        />
                        <ConfigRow 
                            label="Frame Buffer Capacity" 
                            value={config.frame_buffer_capacity} 
                            status="RESTART REQUIRED" 
                            description="Frames buffered per camera to absorb processing spikes." 
                        />
                        <ConfigRow 
                            label="Max Cameras" 
                            value={config.max_cameras} 
                            status="RESTART REQUIRED" 
                            description="Maximum supported hardware ingestion streams." 
                        />
                    </section>
                </div>
            </div>
        </div>
    );
}
