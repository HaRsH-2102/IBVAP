import { useState, useEffect } from 'react';
import { anprApi } from '../api/client';
import { useWs } from '../api/ws';

export default function ANPRCenter() {
    const [reads, setReads] = useState([]);
    const [summary, setSummary] = useState(null);
    const [statusData, setStatusData] = useState(null);
    const [searchPlate, setSearchPlate] = useState('');
    const [selectedRead, setSelectedRead] = useState(null);
    const { events } = useWs();

    const fetchReads = async () => {
        try {
            const res = await anprApi.list({ limit: 100 });
            if (res.ok) setReads(await res.json());
        } catch (e) {
            console.error("fetch ANPR reads failed", e);
        }
    };

    const fetchSummaryAndStatus = async () => {
        try {
            const [sumRes, statRes] = await Promise.all([anprApi.summary(), anprApi.status()]);
            if (sumRes.ok) setSummary(await sumRes.json());
            if (statRes.ok) setStatusData(await statRes.json());
        } catch (e) {
            console.error("fetch ANPR summary/status failed", e);
        }
    };

    useEffect(() => {
        fetchReads();
        fetchSummaryAndStatus();
    }, []);

    useEffect(() => {
        if (events.length > 0) {
            const latest = events[0];
            if (latest.type === 'ANPR_READ') {
                fetchReads();
                fetchSummaryAndStatus();
            }
        }
    }, [events]);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!searchPlate.trim()) {
            fetchReads();
            return;
        }
        try {
            const res = await anprApi.search(searchPlate.trim());
            if (res.ok) {
                setReads(await res.json());
            } else {
                setReads([]);
            }
        } catch (error) {
            setReads([]);
        }
    };

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-6 gap-6 custom-scrollbar overflow-hidden">
            <div className="flex justify-between items-center shrink-0 tech-panel p-6 bg-surface shadow-md">
                <h1 className="font-display-lg text-2xl font-light text-on-surface flex items-center gap-3 tracking-wide">
                    <span className="material-symbols-outlined text-primary text-[28px]">directions_car</span> ANPR Intelligence
                </h1>
                {statusData && (
                    <div className="flex gap-6">
                        <div className="flex items-center gap-3">
                            <span className="font-label-caps text-[11px] uppercase tracking-widest text-outline-variant">Module</span>
                            <span className={`badge ${statusData.enabled ? 'badge-secondary' : 'badge-error'}`}>
                                {statusData.enabled ? 'ONLINE' : 'OFFLINE'}
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="font-label-caps text-[11px] uppercase tracking-widest text-outline-variant">Model</span>
                            <span className="text-on-surface font-data-mono text-[12px] tracking-widest">{statusData.detector_model}</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Metrics */}
            {summary && (
                <div className="grid grid-cols-4 gap-6 shrink-0">
                    <div className="tech-panel p-5 bg-surface flex flex-col gap-2 border-l-4 border-l-primary shadow-md">
                        <span className="font-label-caps text-outline-variant text-[11px] uppercase tracking-widest">Total Reads</span>
                        <span className="font-data-mono text-3xl font-bold text-on-surface tracking-widest">{summary.total_reads}</span>
                    </div>
                    <div className="tech-panel p-5 bg-surface flex flex-col gap-2 border-l-4 border-l-secondary shadow-md">
                        <span className="font-label-caps text-outline-variant text-[11px] uppercase tracking-widest">Unique Plates</span>
                        <span className="font-data-mono text-3xl font-bold text-on-surface tracking-widest">{summary.unique_plates}</span>
                    </div>
                    <div className="col-span-2 tech-panel p-5 bg-surface flex flex-col justify-center border-l-4 border-l-[#ff9900] shadow-md">
                        <span className="font-label-caps text-outline-variant text-[11px] uppercase mb-3 tracking-widest">Class Distribution</span>
                        <div className="flex gap-6 font-data-mono text-[12px] tracking-widest">
                            {Object.entries(summary.by_vehicle_class || {}).map(([cls, count]) => (
                                <div key={cls} className="flex gap-2 items-baseline">
                                    <span className="text-on-surface-variant uppercase">{cls}:</span>
                                    <span className="text-primary font-bold text-lg">{count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            <div className="flex-1 flex gap-6 min-h-0">
                {/* Left: Search & Table */}
                <div className="flex-[2] flex flex-col tech-panel bg-surface shadow-md overflow-hidden">
                    <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim flex justify-between items-center shrink-0">
                        <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest">Plate Directory</span>
                        <form onSubmit={handleSearch} className="flex items-center gap-3">
                            <input 
                                type="text" 
                                placeholder="SEARCH PLATE..."
                                value={searchPlate}
                                onChange={(e) => setSearchPlate(e.target.value.toUpperCase())}
                                className="bg-background border border-outline-variant/50 rounded px-4 py-1.5 text-[12px] tracking-widest font-data-mono text-on-surface focus:outline-none focus:border-primary uppercase w-64 transition-colors"
                            />
                            <button type="submit" className="bg-surface-variant border border-outline-variant/50 hover:border-primary text-on-surface hover:text-primary px-3 py-1.5 rounded transition-colors flex items-center justify-center">
                                <span className="material-symbols-outlined text-[18px]">search</span>
                            </button>
                        </form>
                    </div>
                    <div className="flex-1 overflow-auto bg-background custom-scrollbar">
                        <table className="w-full text-left font-data-mono text-[11px]">
                            <thead className="bg-surface-dim text-outline-variant sticky top-0 z-10 border-b border-outline-variant/50">
                                <tr>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Timestamp</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Plate</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Source</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase text-right">Conf</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Class</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Camera</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reads.map((r, i) => (
                                    <tr 
                                        key={r.event_id + i} 
                                        onClick={() => setSelectedRead(r)}
                                        className={`border-b border-outline-variant/30 cursor-pointer transition-colors group ${selectedRead?.event_id === r.event_id ? 'bg-primary/10 border-l-2 border-l-primary' : 'hover:bg-surface-variant border-l-2 border-l-transparent'}`}
                                    >
                                        <td className="px-6 py-4 text-on-surface-variant tracking-widest group-hover:text-on-surface transition-colors">{new Date(r.timestamp).toISOString().replace('T', ' ').substring(0, 19)}</td>
                                        <td className={`px-6 py-4 font-bold tracking-widest text-lg ${selectedRead?.event_id === r.event_id ? 'text-primary' : 'text-on-surface'}`}>{r.entry_source === 'OPERATOR' ? r.operator_plate_text || r.plate_text : r.plate_text}</td>
                                        <td className="px-6 py-4">
                                            {r.entry_source === 'OPERATOR' ? (
                                                <span className="bg-secondary/10 text-secondary border border-secondary/30 px-2 py-0.5 rounded text-[9px] uppercase tracking-widest whitespace-nowrap">EXTRACTED</span>
                                            ) : (
                                                <span className="text-on-surface-variant text-[10px] uppercase tracking-widest">AI ANPR</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-on-surface-variant tracking-widest text-right">{r.confidence ? `${(r.confidence * 100).toFixed(1)}%` : 'N/A'}</td>
                                        <td className="px-6 py-4 text-on-surface uppercase tracking-widest">{r.vehicle_class}</td>
                                        <td className="px-6 py-4 text-on-surface-variant tracking-widest">{r.camera_id}</td>
                                    </tr>
                                ))}
                                {reads.length === 0 && (
                                    <tr>
                                        <td colSpan="5" className="p-12 text-center text-outline-variant tracking-widest uppercase font-data-mono">
                                            <span className="material-symbols-outlined text-[48px] opacity-20 block mb-4">search_off</span>
                                            NO READS FOUND
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right: Detail */}
                <div className="flex-[1] flex flex-col tech-panel bg-surface shadow-md overflow-hidden min-w-[350px]">
                    <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim shrink-0">
                        <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest">Plate Evidence</span>
                    </div>
                    
                    {selectedRead ? (
                        <div className="p-6 flex flex-col gap-8 overflow-y-auto custom-scrollbar">
                            <div className="flex flex-col items-center p-8 bg-background border border-outline-variant/30 rounded-DEFAULT shadow-[inset_0_0_20px_rgba(0,0,0,0.5)]">
                                <span className="font-data-mono text-[42px] font-bold text-on-surface tracking-[0.2em]">
                                    {selectedRead.entry_source === 'OPERATOR' ? selectedRead.operator_plate_text || selectedRead.plate_text : selectedRead.plate_text}
                                </span>
                                {selectedRead.entry_source === 'OPERATOR' ? (
                                    <span className="mt-4 badge bg-secondary/10 text-secondary border border-secondary/30">
                                        SOURCE: EXTRACTED
                                    </span>
                                ) : (
                                    <span className={`mt-4 badge ${selectedRead.confidence > 0.85 ? 'badge-secondary' : 'bg-[#ff9900]/10 text-[#ff9900] border border-[#ff9900]/30'}`}>
                                        CONF: {(selectedRead.confidence * 100).toFixed(1)}%
                                    </span>
                                )}
                            </div>

                            <div className="flex flex-col gap-4">
                                <h4 className="font-label-caps text-[11px] text-primary uppercase tracking-widest border-b border-outline-variant/30 pb-2">Metadata</h4>
                                <div className="grid grid-cols-2 gap-y-4 gap-x-2 font-data-mono text-[11px] bg-surface-dim p-4 border border-outline-variant/30 rounded">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Event ID</span>
                                        <span className="text-on-surface truncate pr-2 font-bold tracking-widest">{selectedRead.event_id}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Timestamp</span>
                                        <span className="text-on-surface tracking-widest">{new Date(selectedRead.timestamp).toISOString().replace('T', ' ').substring(0, 19)}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Camera</span>
                                        <span className="text-primary tracking-widest">{selectedRead.camera_id}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Track ID</span>
                                        <span className="text-primary tracking-widest">{selectedRead.track_id}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Vehicle Class</span>
                                        <span className="text-on-surface uppercase tracking-widest">{selectedRead.vehicle_class}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Data Source</span>
                                        <span className={`tracking-widest ${selectedRead.entry_source === 'OPERATOR' ? 'text-secondary font-bold' : 'text-on-surface'}`}>
                                            {selectedRead.entry_source === 'OPERATOR' ? 'EXTRACTED' : 'AI ANPR'}
                                        </span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">System Status</span>
                                        <span className="text-on-surface tracking-widest">{selectedRead.status || 'SUCCESS'}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="flex flex-col gap-4">
                                <h4 className="font-label-caps text-[11px] text-primary uppercase tracking-widest border-b border-outline-variant/30 pb-2">Evidence Images</h4>
                                {selectedRead.entry_source !== 'OPERATOR' && (
                                    <div className="flex flex-col gap-2 mb-4">
                                        <span className="font-label-caps text-[10px] text-outline-variant tracking-widest uppercase">Plate Crop</span>
                                        <div className="bg-background border border-outline-variant/30 rounded p-4 flex justify-center items-center min-h-[100px] shadow-[inset_0_0_20px_rgba(0,0,0,0.5)]">
                                            <img 
                                                src={`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/v1/anpr/evidence/${selectedRead.event_id}/plate`}
                                                alt="Plate Crop" 
                                                className="max-h-24 object-contain rounded border border-primary/30"
                                                onError={(e) => {
                                                    e.target.onerror = null;
                                                    e.target.style.display = 'none';
                                                    e.target.parentElement.innerHTML = '<span class="font-data-mono text-[11px] text-outline-variant tracking-widest uppercase">Image unavailable</span>';
                                                }}
                                            />
                                        </div>
                                    </div>
                                )}
                                
                                <div className="flex flex-col gap-2">
                                    <span className="font-label-caps text-[10px] text-outline-variant tracking-widest uppercase">Vehicle Context</span>
                                    <div className="bg-background border border-outline-variant/30 rounded p-4 flex justify-center items-center min-h-[160px] shadow-[inset_0_0_20px_rgba(0,0,0,0.5)]">
                                        <img 
                                            src={`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/v1/events/${selectedRead.event_id}/evidence?type=crop`}
                                            alt="Vehicle Context" 
                                            className="max-h-48 object-contain rounded border border-outline-variant/50"
                                            onError={(e) => {
                                                e.target.onerror = null;
                                                e.target.style.display = 'none';
                                                e.target.parentElement.innerHTML = '<span class="font-data-mono text-[11px] text-outline-variant tracking-widest uppercase">Image unavailable</span>';
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col gap-4 items-center justify-center font-data-mono text-[11px] text-outline-variant p-8 text-center tracking-widest uppercase">
                            <span className="material-symbols-outlined text-[48px] opacity-20">image_search</span>
                            Select a plate record to view evidence and metadata.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
