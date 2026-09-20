import { useState, useEffect } from 'react';
import { cameraApi } from '../api/client';
import { useWs } from '../api/ws';

const CameraSnapshot = ({ camId, tick, isFull = false }) => {
    const [hasError, setHasError] = useState(false);
    const url = `http://127.0.0.1:8000/api/v1/cameras/${camId}/snapshot?t=${tick}`;
    
    useEffect(() => { setHasError(false); }, [tick]);

    return (
        <>
            {!hasError && (
                <img 
                    className="absolute inset-0 w-full h-full object-contain bg-black" 
                    src={url}
                    onError={() => setHasError(true)}
                    alt={`Camera ${camId}`}
                />
            )}
            {hasError && (
                <div className="flex flex-col items-center gap-2 text-outline-variant w-full h-full justify-center bg-[#0c0e12] z-0 relative">
                    <span className={`material-symbols-outlined ${isFull ? 'text-[64px]' : 'text-[32px]'}`}>videocam_off</span>
                    <span className="font-data-mono text-[12px] text-center tracking-widest">FEED UNAVAILABLE</span>
                </div>
            )}
        </>
    );
};

export default function LiveSurveillance() {
    const [cameras, setCameras] = useState([]);
    const [selectedCam, setSelectedCam] = useState(null);
    const [snapshotTick, setSnapshotTick] = useState(0);
    const { status, events } = useWs();

    useEffect(() => {
        const fetchCams = async () => {
            try {
                const res = await cameraApi.list();
                if (res.ok) {
                    const data = await res.json();
                    setCameras(data);
                    if (data.length > 0 && !selectedCam) {
                        setSelectedCam(data[0]);
                    }
                }
            } catch (e) {
                console.error("fetch cameras failed", e);
            }
        };
        fetchCams();
        
        const interval = setInterval(() => setSnapshotTick(prev => prev + 1), 2000);
        return () => clearInterval(interval);
    }, []);

    const recentEvents = events.filter(e => e.type !== 'CAMERA_METRICS').slice(0, 5);

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-6 gap-6 relative">
            <div className="flex justify-between items-center shrink-0">
                <div className="flex items-center gap-4">
                    <h1 className="font-display-lg text-2xl font-light text-on-surface tracking-wide">Surveillance Network</h1>
                    <div className="badge badge-neutral">TOC // LIVE</div>
                </div>
                <div className="flex gap-4">
                    <div className="flex items-center gap-2">
                        <span className="font-label-caps text-[10px] uppercase text-outline-variant tracking-widest">Feed Sync</span>
                        <span className="bg-surface-dim text-secondary px-3 py-1 rounded font-data-mono text-[11px] border border-outline-variant/30">2s INTERVAL</span>
                    </div>
                </div>
            </div>

            <div className="flex-1 flex gap-6 min-h-0">
                {/* Main Hero View */}
                <div className="flex-[3] flex flex-col tech-panel overflow-hidden relative shadow-2xl">
                    {selectedCam ? (
                        <>
                            <div className="absolute top-0 left-0 right-0 p-4 bg-gradient-to-b from-black/80 to-transparent z-10 flex justify-between items-start pointer-events-none">
                                <div className="flex flex-col gap-1">
                                    <div className="flex items-center gap-3">
                                        <span className="w-2 h-2 rounded-full bg-[#ff3333] shadow-[0_0_10px_rgba(255,51,51,0.8)] animate-pulse"></span>
                                        <span className="font-data-mono text-[16px] text-white font-bold tracking-widest shadow-black drop-shadow-md">{selectedCam.camera_id}</span>
                                    </div>
                                    <span className="font-label-caps text-[10px] text-[#00f0ff] uppercase tracking-widest ml-5 shadow-black drop-shadow-md">
                                        {selectedCam.source_type} • {selectedCam.resolution || 'HD'}
                                    </span>
                                </div>
                                
                                <div className="flex flex-col items-end gap-1">
                                    <span className="font-data-mono text-[12px] text-white shadow-black drop-shadow-md">
                                        {new Date().toISOString().substring(11, 19)} UTC
                                    </span>
                                </div>
                            </div>
                            
                            <div className="flex-1 relative bg-black flex items-center justify-center">
                                <CameraSnapshot camId={selectedCam.camera_id} tick={snapshotTick} isFull={true} />
                                
                                {/* Crosshair overlay (subtle cinematic touch) */}
                                <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-10">
                                    <div className="w-[40%] h-px bg-white"></div>
                                    <div className="absolute h-[40%] w-px bg-white"></div>
                                    <div className="absolute w-[30%] h-[30%] border border-white rounded-full"></div>
                                </div>
                            </div>

                            {/* Bottom HUD */}
                            <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 via-black/60 to-transparent z-10 pointer-events-none flex justify-between items-end">
                                <div className="flex gap-6">
                                    <div className="flex flex-col">
                                        <span className="font-label-caps text-[9px] text-outline-variant tracking-widest uppercase">Analysis Status</span>
                                        <span className="font-data-mono text-[12px] text-secondary tracking-widest">{selectedCam.scene_state || 'OPERATIONAL'}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="font-label-caps text-[9px] text-outline-variant tracking-widest uppercase">Pipeline FPS</span>
                                        <span className="font-data-mono text-[12px] text-white tracking-widest">{selectedCam.fps || 0}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="font-label-caps text-[9px] text-outline-variant tracking-widest uppercase">Active Tracks</span>
                                        <span className="font-data-mono text-[12px] text-primary tracking-widest">{selectedCam.active_track_count || 0}</span>
                                    </div>
                                </div>
                                
                                {/* Live Event Stream Overlay */}
                                <div className="w-1/3 flex flex-col gap-1 items-end overflow-hidden h-24 justify-end">
                                    {recentEvents.map((evt, idx) => (
                                        <div key={idx} className="bg-black/50 backdrop-blur-md px-3 py-1 rounded border border-[#262c36]/50 text-right animate-slideInRight">
                                            <span className="font-data-mono text-[10px] text-[#ff9900] mr-2">{evt.type}</span>
                                            <span className="font-data-mono text-[9px] text-outline-variant">{new Date(evt.timestamp || Date.now()).toLocaleTimeString()}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center font-data-mono text-outline-variant bg-surface-dim">
                            <span className="material-symbols-outlined text-[48px] mb-4 opacity-50">videocam_off</span>
                            <span className="tracking-widest text-[12px]">NO CAMERA SELECTED</span>
                        </div>
                    )}
                </div>

                {/* Right: Camera Selector & Info */}
                <div className="w-[320px] flex flex-col gap-6 shrink-0">
                    <div className="tech-panel flex-1 flex flex-col overflow-hidden">
                        <div className="px-4 py-3 border-b border-outline-variant/50 bg-surface-dim backdrop-blur flex justify-between items-center shrink-0">
                            <span className="font-label-caps text-on-surface-variant uppercase text-[11px] tracking-widest">Network Feeds</span>
                            <span className="badge badge-neutral">{cameras.length} ONLINE</span>
                        </div>
                        <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2 custom-scrollbar">
                            {cameras.map(cam => (
                                <div 
                                    key={cam.camera_id} 
                                    onClick={() => setSelectedCam(cam)}
                                    className={`p-3 rounded border cursor-pointer transition-all duration-200 ${
                                        selectedCam?.camera_id === cam.camera_id 
                                            ? 'bg-primary/10 border-primary shadow-[0_0_10px_rgba(0,240,255,0.1)]' 
                                            : 'bg-surface border-outline-variant/30 hover:border-outline-variant hover:bg-surface-variant'
                                    }`}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <span className={`font-data-mono font-bold tracking-widest text-[13px] ${selectedCam?.camera_id === cam.camera_id ? 'text-primary' : 'text-on-surface'}`}>
                                            {cam.camera_id}
                                        </span>
                                        <span className={`w-2 h-2 rounded-full shadow-[0_0_5px_currentColor] ${cam.enabled ? 'bg-secondary text-secondary' : 'bg-[#ff3333] text-[#ff3333]'}`}></span>
                                    </div>
                                    <div className="flex flex-col gap-1 font-label-caps text-[9px] text-outline-variant uppercase tracking-widest">
                                        <div className="flex justify-between">
                                            <span>Type</span>
                                            <span className="text-on-surface-variant">{cam.source_type}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span>Resolution</span>
                                            <span className="text-on-surface-variant">{cam.resolution || 'UNKNOWN'}</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {cameras.length === 0 && (
                                <div className="text-center p-6 text-outline-variant font-data-mono text-[11px] border border-dashed border-outline-variant/30 rounded mt-2 flex flex-col items-center gap-2">
                                    <span className="material-symbols-outlined text-[24px]">videocam_off</span>
                                    NO FEEDS DETECTED
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
