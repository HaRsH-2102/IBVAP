import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { videoApi, zoneApi, validationApi } from '../api/client';
import ZoneDrawingOverlay from '../components/ZoneDrawingOverlay';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export default function Zones() {
    const navigate = useNavigate();
    
    // States: 'VIDEO_SELECTION', 'CONFIGURATION'
    const [viewState, setViewState] = useState('VIDEO_SELECTION');
    
    // Video Selection State
    const [videos, setVideos] = useState([]);
    const [selectedVideo, setSelectedVideo] = useState(null);
    const [newVideoName, setNewVideoName] = useState('');
    const [newVideoPath, setNewVideoPath] = useState('');
    const [isAddingVideo, setIsAddingVideo] = useState(false);
    
    // Zone & Line Data for selected video
    const [zones, setZones] = useState([]);
    const [lines, setLines] = useState([]);

    // Drawing State (used in CONFIGURATION)
    const [drawingMode, setDrawingMode] = useState('IDLE');
    const [selectedId, setSelectedId] = useState(null);
    const [selectedType, setSelectedType] = useState(null);
    const [currentPoints, setCurrentPoints] = useState([]);

    // Dialog state for naming new zones/fences
    const [showConfigDialog, setShowConfigDialog] = useState(false);
    const [configType, setConfigType] = useState(null); // 'zone' or 'line'
    const [configName, setConfigName] = useState('');
    const [configZoneType, setConfigZoneType] = useState('RESTRICTED');
    const [pendingGeometry, setPendingGeometry] = useState(null);

    useEffect(() => {
        if (viewState === 'VIDEO_SELECTION') {
            fetchVideos();
        }
    }, [viewState]);

    const fetchVideos = async () => {
        try {
            const res = await videoApi.list();
            if (res.ok) setVideos(await res.json());
        } catch (e) {
            console.error("Failed to fetch videos", e);
        }
    };

    const handleAddVideo = async (e) => {
        e.preventDefault();
        try {
            const res = await videoApi.create({ name: newVideoName, file_path: newVideoPath });
            if (res.ok) {
                setNewVideoName('');
                setNewVideoPath('');
                setIsAddingVideo(false);
                fetchVideos();
            }
        } catch (err) {
            console.error("Add video failed", err);
            alert("Failed to add video. Check path.");
        }
    };

    const handleDeleteVideo = async (id) => {
        try {
            const res = await videoApi.delete(id);
            if (res.ok) fetchVideos();
        } catch (e) {
            console.error("Delete video failed", e);
        }
    };

    const handleSelectVideo = async (video) => {
        setSelectedVideo(video);
        
        // Fetch zones and lines for this video
        try {
            const [zRes, lRes] = await Promise.all([
                zoneApi.list(video.id),
                zoneApi.listLines(video.id)
            ]);
            if (zRes.ok) setZones(await zRes.json());
            if (lRes.ok) setLines(await lRes.json());
        } catch (e) {
            console.error('Failed to load zones for video', e);
        }
        
        setViewState('CONFIGURATION');
    };

    const handleSaveZonePrompt = () => {
        if (currentPoints.length < 3) {
            alert('Add at least 3 points to create a restricted area.');
            return;
        }
        setPendingGeometry(currentPoints);
        setConfigType('zone');
        setConfigName('');
        setConfigZoneType('RESTRICTED');
        setShowConfigDialog(true);
    };

    const handleSaveLinePrompt = () => {
        if (currentPoints.length < 2) {
            alert('Add at least 2 points to create a fence.');
            return;
        }
        setPendingGeometry(currentPoints);
        setConfigType('line');
        setConfigName('');
        setShowConfigDialog(true);
    };

    const handleCancelDrawing = () => {
        setCurrentPoints([]);
        setDrawingMode('IDLE');
    };

    const handleUndo = () => {
        setCurrentPoints(prev => prev.slice(0, -1));
    };



    const confirmSave = async () => {
        if (!pendingGeometry) return;
        
        const name = configName.trim() || (configType === 'zone' ? `Zone ${zones.length + 1}` : `Fence ${lines.length + 1}`);
        
        try {
            if (configType === 'zone') {
                const res = await zoneApi.create({
                    name,
                    camera_id: selectedVideo.id,
                    zone_type: configZoneType,
                    geometry: pendingGeometry,
                });
                if (res.ok) {
                    const saved = await res.json();
                    setZones(prev => [...prev, saved]);
                }
            } else {
                const res = await zoneApi.createLine({
                    name,
                    camera_id: selectedVideo.id,
                    points: pendingGeometry,
                });
                if (res.ok) {
                    const saved = await res.json();
                    setLines(prev => [...prev, saved]);
                }
            }
        } catch (e) {
            console.error('Save failed', e);
        }
        
        setShowConfigDialog(false);
        setPendingGeometry(null);
        setCurrentPoints([]);
        setDrawingMode('IDLE');
    };

    const handleUpdateZone = async (id, data) => {
        try { await zoneApi.update(id, data); } catch(e) {}
    };

    const handleUpdateLine = async (id, data) => {
        try { await zoneApi.updateLine(id, data); } catch(e) {}
    };

    const handleDeleteSelected = async () => {
        if (!selectedId) return;
        try {
            if (selectedType === 'zone') {
                const res = await zoneApi.remove(selectedId);
                if (res.ok) {
                    setZones(prev => prev.filter(z => z.zone_id !== selectedId));
                    setSelectedId(null);
                }
            } else if (selectedType === 'line') {
                const res = await zoneApi.removeLine(selectedId);
                if (res.ok) {
                    setLines(prev => prev.filter(l => l.line_id !== selectedId));
                    setSelectedId(null);
                }
            }
        } catch(e) { console.error('Delete failed', e); }
    };

    const handleFinishConfiguration = async () => {
        try {
            // First check if a session is already running
            const statusRes = await validationApi.status();
            if (statusRes.ok) {
                const data = await statusRes.json();
                if (data.is_running && data.video_id === selectedVideo.id) {
                    // Session already exists for this video, we just resume it
                    await validationApi.play();
                    navigate('/live-validation');
                    return;
                }
            }
            
            // Otherwise start a new session
            const res = await validationApi.start(selectedVideo.id);
            if (res.ok) {
                navigate('/live-validation');
            } else {
                alert("Failed to start surveillance.");
            }
        } catch (e) {
            console.error("Start surveillance failed", e);
        }
    };

    if (viewState === 'VIDEO_SELECTION') {
        return (
            <div className="h-full bg-surface-container-lowest p-8 overflow-auto custom-scrollbar">
                <div className="max-w-5xl mx-auto flex flex-col gap-8">
                    <div className="flex justify-between items-center bg-surface tech-panel p-6 shadow-md">
                        <div>
                            <h1 className="font-display-lg text-2xl font-light text-on-surface tracking-wide flex items-center gap-3">
                                <span className="material-symbols-outlined text-primary text-[28px]">movie</span>
                                Demo Video Sources
                            </h1>
                            <p className="font-data-mono text-outline-variant text-[11px] tracking-widest mt-2 uppercase">Select a video to configure zones and start the demonstration.</p>
                        </div>
                        <button onClick={() => setIsAddingVideo(!isAddingVideo)} className={`px-5 py-2.5 rounded font-label-caps text-[11px] uppercase tracking-widest flex items-center gap-2 transition-all ${isAddingVideo ? 'bg-surface-variant border border-outline-variant/50 text-on-surface hover:text-error' : 'bg-primary text-black hover:bg-primary/90 shadow-[0_0_15px_rgba(0,240,255,0.3)]'}`}>
                            <span className="material-symbols-outlined text-[16px]">{isAddingVideo ? 'close' : 'add'}</span>
                            {isAddingVideo ? 'Cancel' : 'Add Video'}
                        </button>
                    </div>

                    {isAddingVideo && (
                        <div className="tech-panel p-6 bg-surface shadow-lg border-t-2 border-t-primary">
                            <form onSubmit={handleAddVideo} className="flex gap-6 items-end">
                                <div className="flex-1 flex flex-col gap-2">
                                    <label className="font-label-caps text-[10px] tracking-widest text-primary uppercase">Display Name</label>
                                    <input required type="text" value={newVideoName} onChange={e => setNewVideoName(e.target.value)} className="w-full bg-surface-dim border border-outline-variant/30 rounded p-3 text-[13px] text-on-surface outline-none focus:border-primary focus:shadow-[0_0_10px_rgba(0,240,255,0.1)] transition-all font-data-mono" placeholder="e.g. Border Road Night" />
                                </div>
                                <div className="flex-[2] flex flex-col gap-2">
                                    <label className="font-label-caps text-[10px] tracking-widest text-primary uppercase">Absolute File Path (Server)</label>
                                    <input required type="text" value={newVideoPath} onChange={e => setNewVideoPath(e.target.value)} className="w-full bg-surface-dim border border-outline-variant/30 rounded p-3 text-[13px] text-on-surface outline-none focus:border-primary focus:shadow-[0_0_10px_rgba(0,240,255,0.1)] transition-all font-data-mono" placeholder="e.g. C:\videos\camera_01.mkv" />
                                </div>
                                <button type="submit" className="px-8 py-3 bg-secondary text-black rounded font-label-caps text-[11px] uppercase tracking-widest hover:bg-secondary/90 transition-all shadow-[0_0_15px_rgba(0,255,166,0.3)]">
                                    Save
                                </button>
                            </form>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {videos.map(v => (
                            <div key={v.id} className="tech-panel p-6 bg-surface flex flex-col justify-between group hover:border-primary/50 transition-colors shadow-md hover:shadow-[0_0_20px_rgba(0,240,255,0.1)]">
                                <div>
                                    <div className="flex justify-between items-start mb-4">
                                        <h3 className="font-display-lg text-xl text-on-surface tracking-wide">{v.name}</h3>
                                        <button onClick={() => handleDeleteVideo(v.id)} className="text-outline-variant hover:text-[#ff3333] opacity-0 group-hover:opacity-100 transition-opacity">
                                            <span className="material-symbols-outlined text-[20px]">delete</span>
                                        </button>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3 text-[10px] font-data-mono text-on-surface-variant uppercase tracking-widest bg-surface-dim p-4 rounded border border-outline-variant/30">
                                        <p className="flex items-center gap-2"><span className="material-symbols-outlined text-[14px] text-outline-variant">movie</span> {v.container || 'Unknown Container'}</p>
                                        <p className="flex items-center gap-2"><span className="material-symbols-outlined text-[14px] text-outline-variant">code</span> {v.codec || 'Unknown Codec'}</p>
                                        <p className="flex items-center gap-2"><span className="material-symbols-outlined text-[14px] text-outline-variant">hd</span> {v.resolution || 'Unknown'}</p>
                                        <p className="flex items-center gap-2"><span className="material-symbols-outlined text-[14px] text-outline-variant">schedule</span> {v.duration_sec ? `${Math.round(v.duration_sec)}s` : 'Unknown'} @ {v.fps ? `${Math.round(v.fps * 100) / 100} FPS` : 'Unknown FPS'}</p>
                                    </div>
                                </div>
                                <button onClick={() => handleSelectVideo(v)} className="w-full mt-6 py-3 bg-surface-variant border border-outline-variant/50 rounded text-on-surface hover:text-primary font-label-caps text-[10px] uppercase tracking-widest hover:border-primary transition-all">
                                    Select & Configure
                                </button>
                            </div>
                        ))}
                        {videos.length === 0 && !isAddingVideo && (
                            <div className="col-span-full py-16 text-center text-outline-variant flex flex-col items-center gap-4">
                                <span className="material-symbols-outlined text-[64px] opacity-20">movie</span>
                                <p className="font-data-mono text-[12px] uppercase tracking-widest">No videos available. Click "Add Video" to begin.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-full bg-surface-container-lowest overflow-hidden relative">
            <div className="flex-1 flex flex-col p-6 gap-6 overflow-hidden relative">
                
                {/* Header Row */}
                <div className="flex justify-between items-center shrink-0 tech-panel p-6 bg-surface">
                    <div className="flex flex-col gap-2">
                        <h1 className="font-display-lg text-2xl font-light text-on-surface tracking-wide flex items-center gap-3">
                            <span className="material-symbols-outlined text-primary text-[28px]">format_shapes</span>
                            Zones & Tripwires
                        </h1>
                        <p className="font-data-mono text-[11px] text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                            <span className="material-symbols-outlined text-[14px]">videocam</span> {selectedVideo?.name}
                        </p>
                    </div>
                    
                    <div className="flex gap-4 items-center">
                        <button onClick={() => setViewState('VIDEO_SELECTION')} className="px-5 py-2 border border-outline-variant/50 rounded font-label-caps text-[10px] uppercase tracking-widest text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors">
                            Return to Source List
                        </button>
                        <button onClick={handleFinishConfiguration} className="px-6 py-2 bg-primary text-black rounded font-label-caps text-[11px] uppercase tracking-widest hover:bg-primary/90 transition-all flex items-center gap-2 shadow-[0_0_15px_rgba(0,240,255,0.3)]">
                            <span className="material-symbols-outlined text-[18px]">play_arrow</span>
                            Start Surveillance
                        </button>
                    </div>
                </div>

                {/* Configuration Toolbar */}
                <div className="tech-panel p-3 bg-surface-dim flex gap-3 items-center shrink-0">
                    {drawingMode === 'IDLE' || drawingMode === 'EDIT' ? (
                        <>
                            <button
                                onClick={() => { setDrawingMode(drawingMode === 'DRAW_ZONE' ? 'IDLE' : 'DRAW_ZONE'); setSelectedId(null); }}
                                className={`px-4 py-2 rounded text-[11px] font-label-caps uppercase tracking-widest border flex items-center gap-2 transition-colors ${
                                    drawingMode === 'DRAW_ZONE' ? 'bg-[#ff3333]/20 border-[#ff3333] text-[#ff3333]' : 'border-outline-variant/30 bg-surface text-on-surface hover:border-outline-variant'
                                }`}
                            >
                                <span className="material-symbols-outlined text-[16px]">draw</span>
                                Add Restricted Area
                            </button>
                            <button
                                onClick={() => { setDrawingMode(drawingMode === 'DRAW_FENCE' ? 'IDLE' : 'DRAW_FENCE'); setSelectedId(null); }}
                                className={`px-4 py-2 rounded text-[11px] font-label-caps uppercase tracking-widest border flex items-center gap-2 transition-colors ${
                                    drawingMode === 'DRAW_FENCE' ? 'bg-primary/20 border-primary text-primary' : 'border-outline-variant/30 bg-surface text-on-surface hover:border-outline-variant'
                                }`}
                            >
                                <span className="material-symbols-outlined text-[16px]">polyline</span>
                                Add Virtual Fence
                            </button>
                            <div className="w-px h-6 bg-outline-variant/30 mx-2"></div>
                            <button
                                onClick={() => { setDrawingMode(drawingMode === 'EDIT' ? 'IDLE' : 'EDIT'); }}
                                className={`px-4 py-2 rounded text-[11px] font-label-caps uppercase tracking-widest border flex items-center gap-2 transition-colors ${
                                    drawingMode === 'EDIT' ? 'bg-secondary/20 border-secondary text-secondary' : 'border-outline-variant/30 bg-surface text-on-surface hover:border-outline-variant'
                                }`}
                            >
                                <span className="material-symbols-outlined text-[16px]">edit</span>
                                Edit Geometry
                            </button>
                            {drawingMode === 'EDIT' && selectedId && (
                                <button
                                    onClick={handleDeleteSelected}
                                    className="px-4 py-2 rounded text-[11px] font-label-caps uppercase tracking-widest border border-[#ff3333] text-[#ff3333] hover:bg-[#ff3333]/10 flex items-center gap-2 transition-colors ml-2"
                                >
                                    <span className="material-symbols-outlined text-[16px]">delete</span>
                                    Delete Selected
                                </button>
                            )}
                        </>
                    ) : (
                        <>
                            <span className="font-label-caps text-primary text-[11px] tracking-widest px-4 uppercase border border-primary/30 bg-primary/5 py-2 rounded">
                                {drawingMode === 'DRAW_ZONE' ? 'DRAWING RESTRICTED AREA' : 'DRAWING VIRTUAL FENCE'}
                            </span>
                            <div className="w-px h-6 bg-outline-variant/30 mx-2"></div>
                            <button onClick={handleUndo} className="px-4 py-2 border border-outline-variant/50 bg-surface rounded font-label-caps text-[11px] text-on-surface hover:text-primary hover:border-primary flex items-center gap-2 transition-colors uppercase tracking-widest">
                                <span className="material-symbols-outlined text-[16px]">undo</span> Undo
                            </button>
                            <button onClick={drawingMode === 'DRAW_ZONE' ? handleSaveZonePrompt : handleSaveLinePrompt} className="px-4 py-2 rounded font-label-caps uppercase tracking-widest text-[11px] bg-secondary/20 text-secondary border border-secondary/50 hover:bg-secondary/30 flex items-center gap-2 transition-colors shadow-[0_0_10px_rgba(0,255,166,0.1)]">
                                <span className="material-symbols-outlined text-[16px]">check</span> Finish Drawing
                            </button>
                            <button onClick={handleCancelDrawing} className="px-4 py-2 border border-[#ff3333]/50 bg-surface rounded font-label-caps uppercase tracking-widest text-[11px] text-[#ff3333] hover:bg-[#ff3333]/10 flex items-center gap-2 transition-colors">
                                <span className="material-symbols-outlined text-[16px]">close</span> Cancel
                            </button>
                        </>
                    )}
                    
                    <div className="flex-1"></div>
                    <span className="text-[10px] text-outline-variant font-data-mono uppercase tracking-widest bg-background px-4 py-2 border border-outline-variant/30 rounded">
                        {drawingMode === 'IDLE' ? 'Static Frame — Draw zones before starting' : 
                         drawingMode === 'EDIT' ? 'Click geometry to select. Drag vertices to edit.' : 
                         'Click to place points'}
                    </span>
                </div>

                {/* Video Area */}
                <div className="flex-1 tech-panel overflow-hidden flex flex-col min-h-0 relative bg-surface">
                    <div className="flex-1 bg-black relative flex items-center justify-center overflow-hidden">

                        <div className="relative w-full h-full flex items-center justify-center">
                            <img 
                                src={`${API_BASE_URL}/videos/${selectedVideo.id}/frame`} 
                                alt="Static Configuration Frame" 
                                className="max-w-full max-h-full object-contain pointer-events-none select-none"
                                draggable="false"
                            />
                            
                            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                <ZoneDrawingOverlay 
                                    mode={drawingMode} 
                                    onModeChange={setDrawingMode} 
                                    zones={zones}
                                    setZones={setZones}
                                    lines={lines}
                                    setLines={setLines}
                                    onSaveZone={handleSaveZonePrompt}
                                    onSaveLine={handleSaveLinePrompt}
                                    onUpdateZone={handleUpdateZone}
                                    onUpdateLine={handleUpdateLine}
                                    selectedId={selectedId}
                                    setSelectedId={setSelectedId}
                                    setSelectedType={setSelectedType}
                                    currentPoints={currentPoints}
                                    setCurrentPoints={setCurrentPoints}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Config Dialog Modal */}
            {showConfigDialog && (
                <div className="absolute inset-0 bg-background/90 backdrop-blur-sm z-50 flex items-center justify-center">
                    <div className="tech-panel bg-surface border border-outline-variant/30 rounded p-8 w-[400px] shadow-2xl">
                        <h3 className="font-display-lg text-xl font-light text-on-surface mb-6 tracking-wide">
                            Save {configType === 'zone' ? 'Restricted Area' : 'Virtual Fence'}
                        </h3>
                        <div className="space-y-6">
                            <div className="flex flex-col gap-2">
                                <label className="font-label-caps text-[10px] tracking-widest text-primary uppercase">Name</label>
                                <input 
                                    type="text" 
                                    value={configName} 
                                    onChange={(e) => setConfigName(e.target.value)}
                                    className="w-full bg-surface-dim border border-outline-variant/30 rounded p-3 text-[13px] text-on-surface focus:border-primary outline-none transition-colors font-data-mono"
                                    placeholder="e.g. North Perimeter"
                                    autoFocus
                                />
                            </div>
                            {configType === 'zone' && (
                                <div className="flex flex-col gap-2">
                                    <label className="font-label-caps text-[10px] tracking-widest text-primary uppercase">Zone Type</label>
                                    <select 
                                        value={configZoneType} 
                                        onChange={(e) => setConfigZoneType(e.target.value)}
                                        className="w-full bg-surface-dim border border-outline-variant/30 rounded p-3 text-[13px] text-on-surface focus:border-primary outline-none transition-colors font-data-mono"
                                    >
                                        <option value="RESTRICTED">Restricted Area</option>
                                        <option value="LOITERING">Loitering Detection</option>
                                    </select>
                                </div>
                            )}
                            <div className="flex justify-end gap-4 pt-4 border-t border-outline-variant/30">
                                <button 
                                    onClick={() => { setShowConfigDialog(false); setPendingGeometry(null); }}
                                    className="px-6 py-2.5 border border-outline-variant/50 rounded text-[11px] font-label-caps uppercase tracking-widest text-on-surface hover:text-primary hover:border-primary transition-colors"
                                >
                                    Cancel
                                </button>
                                <button 
                                    onClick={confirmSave}
                                    className="px-6 py-2.5 bg-primary text-black rounded text-[11px] font-label-caps uppercase tracking-widest hover:bg-primary/90 transition-colors shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                                >
                                    Save Geometry
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
