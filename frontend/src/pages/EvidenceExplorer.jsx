import { useState, useEffect } from 'react';
import { eventApi } from '../api/client';

export default function EvidenceExplorer() {
    const [events, setEvents] = useState([]);
    const [selectedEvidence, setSelectedEvidence] = useState(null);
    const [imageType, setImageType] = useState('crop');
    const [assignModalOpen, setAssignModalOpen] = useState(false);
    const [manualPlateText, setManualPlateText] = useState('');
    const [assigning, setAssigning] = useState(false);

    const fetchEvents = async () => {
        try {
            const res = await eventApi.list({ limit: 100 });
            if (res.ok) {
                const data = await res.json();
                setEvents(data.filter(e => e.evidence));
            }
        } catch (e) {
            console.error("fetch events failed", e);
        }
    };

    useEffect(() => {
        fetchEvents();
    }, []);

    const renderCountdown = (expiresAt) => {
        if (!expiresAt) return 'Unknown';
        const ms = new Date(expiresAt) - new Date();
        if (ms <= 0) return 'Expired';
        const hours = Math.floor(ms / 3600000);
        const mins = Math.floor((ms % 3600000) / 60000);
        return `${hours}h ${mins}m remaining`;
    };

    const handleAssignPlate = async () => {
        if (!manualPlateText || !manualPlateText.trim()) return;
        setAssigning(true);
        try {
            const normalizedPlate = manualPlateText.trim().toUpperCase().replace(/\s+/g, '');
            const res = await eventApi.overridePlate(selectedEvidence.event_id, { plate_text: normalizedPlate });
            if (res.ok) {
                setAssignModalOpen(false);
                setManualPlateText('');
                await fetchEvents();
                // Update selected evidence from new list
                const updated = await eventApi.get(selectedEvidence.event_id);
                if (updated.ok) {
                    const data = await updated.json();
                    setSelectedEvidence(data);
                }
            }
        } catch (e) {
            console.error("Failed to assign plate", e);
        } finally {
            setAssigning(false);
        }
    };

    const isVehicle = (e) => {
        if (!e) return false;
        const classes = [
            e.evidence?.object_class,
            e.metadata?.object_class,
            e.metadata?.vehicle_class,
            e.anpr?.vehicle_class,
            e.object_class,
            e.vehicle_class
        ];
        
        for (const cls of classes) {
            if (typeof cls === 'string') {
                const normalized = cls.toLowerCase().trim();
                if (['car', 'truck', 'bus', 'motorcycle', 'bike', 'vehicle'].includes(normalized)) {
                    return true;
                }
            }
        }
        return false;
    };

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-6 gap-6">
            <div className="flex justify-between items-center shrink-0">
                <h1 className="font-display-lg text-2xl font-light text-on-surface flex items-center gap-3 tracking-wide">
                    <span className="material-symbols-outlined text-primary text-[28px]">image</span> Evidence Explorer
                </h1>
                <div className="badge badge-neutral tracking-widest uppercase">
                    {events.length} RECORDS FOUND
                </div>
            </div>

            <div className="flex-1 flex gap-6 min-h-0">
                {/* Left: Events with Evidence */}
                <div className="flex-[2] tech-panel flex flex-col overflow-hidden bg-surface">
                    <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim flex justify-between items-center shrink-0">
                        <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest">Evidence Registry</span>
                    </div>
                    <div className="flex-1 overflow-auto bg-background custom-scrollbar">
                        <table className="w-full text-left font-data-mono text-[11px]">
                            <thead className="bg-surface-dim text-outline-variant sticky top-0 z-10 border-b border-outline-variant/50">
                                <tr>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Timestamp</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Event Type</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Camera</th>
                                </tr>
                            </thead>
                            <tbody>
                                {events.map((e, i) => (
                                    <tr 
                                        key={e.event_id + i}
                                        onClick={() => {
                                            setSelectedEvidence(e);
                                            setImageType('crop');
                                        }}
                                        className={`border-b border-outline-variant/30 cursor-pointer transition-colors ${selectedEvidence?.event_id === e.event_id ? 'bg-primary/10 shadow-[inset_2px_0_0_0_rgba(0,240,255,1)]' : 'hover:bg-surface-variant'}`}
                                    >
                                        <td className="px-6 py-4 text-on-surface-variant">{new Date(e.timestamp).toISOString().replace('T', ' ').substring(0, 19)}</td>
                                        <td className="px-6 py-4 text-primary font-bold uppercase tracking-widest flex items-center gap-2">
                                            {e.event_type}
                                            {e.anpr?.entry_source === 'OPERATOR' && (
                                                <span className="bg-secondary/10 text-secondary border border-secondary/30 px-1.5 py-0.5 rounded text-[9px] whitespace-nowrap">
                                                    {e.anpr.operator_plate_text}
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-on-surface-variant tracking-widest">{e.camera_id}</td>
                                    </tr>
                                ))}
                                {events.length === 0 && (
                                    <tr>
                                        <td colSpan="3" className="p-12 text-center text-outline-variant font-data-mono tracking-widest uppercase">
                                            <span className="material-symbols-outlined text-[48px] opacity-20 block mb-4">image_not_supported</span>
                                            NO EVIDENCE FOUND
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right: Evidence Viewer */}
                <div className="flex-[3] flex flex-col tech-panel overflow-hidden bg-surface">
                    <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim shrink-0 flex justify-between items-center z-10">
                        <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest">Evidence Viewer</span>
                        {selectedEvidence && (
                            <div className="flex gap-2 p-1 bg-background rounded border border-outline-variant/30">
                                <button 
                                    onClick={() => setImageType('crop')}
                                    className={`px-4 py-1.5 text-[10px] font-bold tracking-widest rounded uppercase transition-colors ${imageType === 'crop' ? 'bg-primary text-black shadow-[0_0_10px_rgba(0,240,255,0.2)]' : 'text-on-surface-variant hover:text-on-surface'}`}
                                >
                                    OBJECT CROP
                                </button>
                                <button 
                                    onClick={() => setImageType('full')}
                                    className={`px-4 py-1.5 text-[10px] font-bold tracking-widest rounded uppercase transition-colors ${imageType === 'full' ? 'bg-primary text-black shadow-[0_0_10px_rgba(0,240,255,0.2)]' : 'text-on-surface-variant hover:text-on-surface'}`}
                                >
                                    FULL SCENE
                                </button>
                                {selectedEvidence.anpr && selectedEvidence.anpr.plate_crop_path && (
                                    <button 
                                        onClick={() => setImageType('plate')}
                                        className={`px-4 py-1.5 text-[10px] font-bold tracking-widest rounded uppercase transition-colors ${imageType === 'plate' ? 'bg-primary text-black shadow-[0_0_10px_rgba(0,240,255,0.2)]' : 'text-on-surface-variant hover:text-on-surface'}`}
                                    >
                                        PLATE CROP
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                    
                    <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col">
                        <div className="relative bg-black p-1 flex items-center justify-center shrink-0 min-h-[50vh]">
                            {selectedEvidence ? (
                                <img 
                                    key={`${selectedEvidence.event_id}-${imageType}`}
                                    className="w-full h-full object-contain" 
                                    src={`http://127.0.0.1:8000/api/v1/events/${selectedEvidence.event_id}/evidence?type=${imageType}`}
                                    onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                                    alt="Evidence"
                                />
                            ) : (
                                <div className="text-outline-variant font-data-mono flex flex-col items-center gap-4">
                                    <span className="material-symbols-outlined text-[48px] opacity-20">touch_app</span>
                                    <span className="tracking-widest uppercase text-[10px]">SELECT AN EVENT TO VIEW EVIDENCE</span>
                                </div>
                            )}
                            <div style={{display: 'none'}} className="flex-col items-center gap-4 text-outline-variant font-data-mono">
                                <span className="material-symbols-outlined text-[48px] opacity-20 text-error">broken_image</span>
                                <span className="tracking-widest uppercase text-[10px] text-error">IMAGE FILE NOT FOUND ON DISK</span>
                            </div>
                        </div>
                        
                        {selectedEvidence && (
                            <div className="p-6 bg-surface-dim border-t border-outline-variant/50 flex flex-col gap-8 font-data-mono text-[11px] text-on-surface-variant shrink-0">
                                <div>
                                    <div className="border-b border-outline-variant/30 pb-2 mb-4">
                                        <span className="font-label-caps text-[10px] tracking-widest text-primary">EVENT DETAILS</span>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Event</span>
                                            <span className="text-primary font-bold tracking-widest">{selectedEvidence.event_type}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Camera</span>
                                            <span className="text-primary truncate block tracking-widest">{selectedEvidence.camera_id}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Object</span>
                                            <span className="text-on-surface tracking-widest uppercase">{selectedEvidence?.evidence?.object_class || selectedEvidence?.metadata?.object_class || selectedEvidence?.anpr?.vehicle_class || 'UNKNOWN'}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Timestamp</span>
                                            <span className="text-on-surface">{new Date(selectedEvidence.timestamp).toLocaleTimeString()}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Track ID</span>
                                            <span className="text-on-surface truncate block tracking-widest">{selectedEvidence.track_id}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Event ID</span>
                                            <span className="text-on-surface truncate block tracking-widest" title={selectedEvidence.event_id}>{selectedEvidence.event_id}</span>
                                        </div>
                                    </div>
                                </div>
                                
                                <div>
                                    <div className="border-b border-outline-variant/30 pb-2 mb-4">
                                        <span className="font-label-caps text-[10px] tracking-widest text-primary">EVIDENCE STATUS</span>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Status</span>
                                            <span className={`tracking-widest ${selectedEvidence.evidence.is_saved ? 'text-secondary' : 'text-[#ff9900]'}`}>
                                                {selectedEvidence.evidence.is_saved ? 'SAVED' : 'TEMPORARY'}
                                            </span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Expiration</span>
                                            <span className="text-on-surface tracking-widest">
                                                {selectedEvidence.evidence.is_saved ? 'PERMANENT' : renderCountdown(selectedEvidence.evidence.expires_at)}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {isVehicle(selectedEvidence) && (
                                    <div>
                                        <div className="border-b border-outline-variant/30 pb-2 mb-4">
                                            <span className="font-label-caps text-[10px] tracking-widest text-primary">VEHICLE ACTIONS</span>
                                        </div>
                                        <button 
                                            onClick={() => setAssignModalOpen(true)}
                                            className="bg-primary/10 text-primary border border-primary/40 hover:bg-primary/20 hover:border-primary/60 w-full py-4 rounded uppercase tracking-widest font-bold flex items-center justify-center gap-3 shadow-[0_0_15px_rgba(0,240,255,0.1)] transition-all"
                                        >
                                            <span className="material-symbols-outlined text-[20px]">add_box</span>
                                            ASSIGN VEHICLE NUMBER
                                        </button>
                                    </div>
                                )}

                            {selectedEvidence.anpr && (
                                <div>
                                    <div className="border-b border-outline-variant/30 pb-2 mb-4">
                                        <span className="font-label-caps text-[10px] tracking-widest text-primary">ANPR ANALYSIS</span>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">License Plate</span>
                                            {selectedEvidence.anpr.entry_source === 'OPERATOR' ? (
                                                <span className="font-bold tracking-widest text-[14px] text-[#00f0ff]">
                                                    {selectedEvidence.anpr.operator_plate_text}
                                                </span>
                                            ) : (
                                                <span className={`font-bold tracking-widest text-[14px] ${selectedEvidence.anpr.status.includes('FAIL') || selectedEvidence.anpr.status === 'NO_PLATE' ? 'text-error' : 'text-[#00f0ff]'}`}>
                                                    {selectedEvidence.anpr.status === 'NO_PLATE' ? 'NO PLATE DETECTED' : (selectedEvidence.anpr.status.includes('FAIL') ? 'OCR FAILED' : (selectedEvidence.anpr.plate_text_normalized || selectedEvidence.anpr.plate_text_raw || 'UNKNOWN'))}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Source</span>
                                            <span className={`tracking-widest ${selectedEvidence.anpr.entry_source === 'OPERATOR' ? 'text-secondary' : 'text-on-surface'}`}>
                                                {selectedEvidence.anpr.entry_source === 'OPERATOR' ? 'EXTRACTED' : 'AI / SYSTEM'}
                                            </span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">AI ANPR Status</span>
                                            <span className={`tracking-widest ${selectedEvidence.anpr.status.includes('SUCCESS') ? 'text-secondary' : (selectedEvidence.anpr.status.includes('FAIL') ? 'text-error' : 'text-on-surface')}`}>
                                                {selectedEvidence.anpr.status}
                                            </span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">OCR Confidence</span>
                                            <span className="text-on-surface tracking-widest">
                                                {selectedEvidence.anpr.ocr_confidence ? `${(selectedEvidence.anpr.ocr_confidence * 100).toFixed(1)}%` : 'N/A'}
                                            </span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-outline-variant text-[10px] uppercase tracking-widest font-label-caps">Detect Confidence</span>
                                            <span className="text-on-surface tracking-widest">
                                                {selectedEvidence.anpr.plate_confidence ? `${(selectedEvidence.anpr.plate_confidence * 100).toFixed(1)}%` : 'N/A'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                    </div>
                </div>
            </div>

            {/* Manual Assignment Modal */}
            {assignModalOpen && selectedEvidence && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="tech-panel p-6 max-w-md w-full flex flex-col gap-6">
                        <div className="flex items-center gap-3 border-b border-outline-variant/30 pb-4">
                            <span className="material-symbols-outlined text-primary text-[28px]">directions_car</span>
                            <h2 className="font-display-lg text-lg text-on-surface tracking-wide">ASSIGN VEHICLE NUMBER</h2>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4 font-data-mono text-[11px]">
                            <div className="flex flex-col gap-1">
                                <span className="text-outline-variant uppercase tracking-widest font-label-caps text-[10px]">Event</span>
                                <span className="text-primary font-bold">{selectedEvidence.event_type}</span>
                            </div>
                            <div className="flex flex-col gap-1">
                                <span className="text-outline-variant uppercase tracking-widest font-label-caps text-[10px]">Vehicle</span>
                                <span className="text-on-surface uppercase tracking-widest">{selectedEvidence?.evidence?.object_class || selectedEvidence?.metadata?.object_class || selectedEvidence?.anpr?.vehicle_class || 'UNKNOWN'}</span>
                            </div>
                            <div className="flex flex-col gap-1 col-span-2">
                                <span className="text-outline-variant uppercase tracking-widest font-label-caps text-[10px]">Camera</span>
                                <span className="text-on-surface uppercase tracking-widest">{selectedEvidence.camera_id}</span>
                            </div>
                        </div>

                        <div className="flex flex-col gap-2">
                            <label className="text-outline-variant uppercase tracking-widest font-label-caps text-[10px]">Registration Number</label>
                            <input 
                                type="text"
                                autoFocus
                                placeholder="e.g. MH20XX1234"
                                className="bg-surface-dim border border-outline-variant/50 p-3 rounded font-data-mono text-on-surface uppercase tracking-widest focus:border-primary focus:outline-none transition-colors"
                                value={manualPlateText}
                                onChange={(e) => setManualPlateText(e.target.value.toUpperCase())}
                                onKeyDown={(e) => e.key === 'Enter' && handleAssignPlate()}
                            />
                        </div>

                        <div className="flex justify-end gap-4 mt-2">
                            <button 
                                onClick={() => { setAssignModalOpen(false); setManualPlateText(''); }}
                                className="btn-secondary"
                            >
                                CANCEL
                            </button>
                            <button 
                                onClick={handleAssignPlate}
                                disabled={assigning || !manualPlateText.trim()}
                                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {assigning ? 'SAVING...' : 'SAVE'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
