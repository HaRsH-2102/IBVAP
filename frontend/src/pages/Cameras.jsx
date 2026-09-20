import { useState, useEffect } from 'react';
import { cameraApi } from '../api/client';

export default function Cameras() {
    const [cameras, setCameras] = useState([]);
    const [selectedCam, setSelectedCam] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);

    const fetchCams = async () => {
        try {
            const res = await cameraApi.list();
            if (res.ok) {
                setCameras(await res.json());
            }
        } catch (e) {
            console.error("fetch cameras failed", e);
        }
    };

    useEffect(() => {
        fetchCams();
    }, []);

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-6 gap-6">
            <div className="flex justify-between items-center shrink-0">
                <h1 className="font-display-lg text-2xl font-light text-on-surface flex items-center gap-3 tracking-wide">
                    <span className="material-symbols-outlined text-primary text-[28px]">nest_cam_iq_outdoor</span> Cameras
                </h1>
                <button 
                    onClick={() => setShowAddModal(true)}
                    className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-on-primary px-4 py-2 rounded font-label-caps uppercase transition-colors shadow-[0_0_15px_rgba(0,240,255,0.3)]"
                >
                    <span className="material-symbols-outlined text-[18px]">add</span>
                    Add Camera
                </button>
            </div>

            <div className="flex-1 flex gap-6 min-h-0">
                {/* Left: Camera List */}
                <div className="flex-[2] tech-panel flex flex-col overflow-hidden bg-surface">
                    <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim flex justify-between items-center shrink-0">
                        <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest">Hardware Inventory</span>
                        <span className="badge badge-neutral tracking-widest uppercase">{cameras.length} Total</span>
                    </div>
                    <div className="flex-1 overflow-auto bg-background custom-scrollbar">
                        <table className="w-full text-left font-data-mono text-[11px]">
                            <thead className="bg-surface-dim text-outline-variant sticky top-0 z-10 border-b border-outline-variant/50">
                                <tr>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Camera ID</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Status</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Source</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase">Scene</th>
                                    <th className="px-6 py-4 font-medium tracking-widest uppercase text-right">Alerts</th>
                                </tr>
                            </thead>
                            <tbody>
                                {cameras.map((cam, i) => (
                                    <tr 
                                        key={cam.camera_id + i} 
                                        onClick={() => setSelectedCam(cam)}
                                        className={`border-b border-outline-variant/30 cursor-pointer transition-colors ${selectedCam?.camera_id === cam.camera_id ? 'bg-primary/10 shadow-[inset_2px_0_0_0_rgba(0,240,255,1)]' : 'hover:bg-surface-variant'}`}
                                    >
                                        <td className="px-6 py-4 text-primary font-bold tracking-widest">{cam.camera_id}</td>
                                        <td className="px-6 py-4">
                                            <span className={`badge ${cam.enabled ? 'badge-secondary' : 'badge-critical'}`}>
                                                {cam.enabled ? 'Online' : 'Offline'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-on-surface-variant tracking-widest">{cam.source_type}</td>
                                        <td className="px-6 py-4 text-on-surface tracking-widest uppercase">{cam.scene_state || 'UNKNOWN'}</td>
                                        <td className="px-6 py-4 text-right">
                                            {cam.alerts > 0 ? (
                                                <span className="badge badge-critical text-[10px] shadow-[0_0_10px_rgba(255,51,51,0.5)]">{cam.alerts}</span>
                                            ) : (
                                                <span className="text-outline-variant/50 tracking-widest">-</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                                {cameras.length === 0 && (
                                    <tr>
                                        <td colSpan="5" className="p-12 text-center text-outline-variant font-data-mono tracking-widest uppercase">
                                            <span className="material-symbols-outlined text-[48px] opacity-20 block mb-4">videocam_off</span>
                                            NO CAMERAS REGISTERED
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right: Camera Details */}
                <div className="flex-[1] flex flex-col tech-panel overflow-hidden bg-surface min-w-[320px]">
                    <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim shrink-0">
                        <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest">Hardware Details</span>
                    </div>
                    
                    {selectedCam ? (
                        <div className="p-6 flex flex-col gap-8 overflow-y-auto custom-scrollbar">
                            <div className="flex flex-col items-center p-8 bg-background border border-outline-variant/30 rounded">
                                <span className="material-symbols-outlined text-[64px] text-primary mb-4 opacity-80">videocam</span>
                                <span className="font-data-mono text-2xl font-bold text-on-surface tracking-widest">{selectedCam.camera_id}</span>
                                <span className="mt-3 px-3 py-1 bg-surface-dim border border-outline-variant/30 rounded font-data-mono text-[10px] text-outline-variant truncate max-w-full text-center">
                                    {selectedCam.source_uri}
                                </span>
                            </div>

                            <div className="flex flex-col gap-4">
                                <h4 className="font-label-caps text-[10px] text-outline-variant uppercase tracking-widest flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-outline-variant/50"></span>
                                    Configuration
                                </h4>
                                <div className="grid grid-cols-2 gap-4 font-data-mono text-[11px] bg-surface-dim p-4 rounded border border-outline-variant/30">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Pipeline Type</span>
                                        <span className="text-on-surface font-bold tracking-widest uppercase">{selectedCam.pipeline_type}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Source Type</span>
                                        <span className="text-on-surface font-bold tracking-widest uppercase">{selectedCam.source_type}</span>
                                    </div>
                                    <div className="flex flex-col gap-1 col-span-2">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Detection ROI</span>
                                        <span className="text-on-surface tracking-widest uppercase">{selectedCam.config?.detection_roi?.length ? 'CONFIGURED' : 'FULL FRAME'}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="flex flex-col gap-4">
                                <h4 className="font-label-caps text-[10px] text-outline-variant uppercase tracking-widest flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary/50"></span>
                                    Current State
                                </h4>
                                <div className="grid grid-cols-2 gap-4 font-data-mono text-[11px] bg-surface-dim p-4 rounded border border-outline-variant/30">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Scene State</span>
                                        <span className="text-primary font-bold tracking-widest uppercase">{selectedCam.scene_state || 'UNKNOWN'}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">Active Tracks</span>
                                        <span className="text-on-surface tracking-widest font-bold">{selectedCam.active_track_count || 0}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-outline-variant text-[9px] uppercase tracking-widest">FPS</span>
                                        <span className="text-on-surface tracking-widest font-bold">{selectedCam.fps || 0}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="mt-auto pt-6 flex gap-3">
                                <button className="flex-1 bg-surface-variant border border-outline-variant/50 hover:border-primary text-on-surface hover:text-primary px-4 py-2.5 rounded font-label-caps text-[10px] uppercase tracking-widest transition-colors">
                                    Edit Config
                                </button>
                                <button className="flex-1 bg-surface-variant border border-outline-variant/50 hover:border-[#ff3333] text-on-surface hover:text-[#ff3333] px-4 py-2.5 rounded font-label-caps text-[10px] uppercase tracking-widest transition-colors">
                                    Disable
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center font-data-mono text-[11px] text-outline-variant p-8 text-center gap-4">
                            <span className="material-symbols-outlined text-[48px] opacity-20">settings_input_component</span>
                            <span className="tracking-widest uppercase">SELECT A CAMERA TO VIEW CONFIGURATION</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-background/90 backdrop-blur-sm flex items-center justify-center z-50 p-6">
                    <div className="tech-panel bg-surface border border-outline-variant/30 rounded p-8 max-w-md w-full flex flex-col gap-6 shadow-2xl">
                        <div className="flex justify-between items-start">
                            <h2 className="font-display-lg text-2xl font-light text-on-surface tracking-wide">Add Hardware</h2>
                            <button onClick={() => setShowAddModal(false)} className="text-outline-variant hover:text-on-surface transition-colors">
                                <span className="material-symbols-outlined text-[24px]">close</span>
                            </button>
                        </div>
                        <div className="py-8 flex flex-col items-center justify-center gap-6 text-center">
                            <div className="w-16 h-16 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-primary shadow-[0_0_15px_rgba(0,240,255,0.15)]">
                                <span className="material-symbols-outlined text-[32px]">router</span>
                            </div>
                            <p className="font-data-mono text-sm text-on-surface-variant tracking-wide leading-relaxed">Hardware discovery is required to add new surveillance nodes.</p>
                            <p className="font-label-caps text-[10px] tracking-widest text-[#ff9900] bg-[#ff9900]/10 border border-[#ff9900]/30 px-3 py-1.5 rounded uppercase">Milestone 14 Feature: Node Provisioning</p>
                        </div>
                        <button onClick={() => setShowAddModal(false)} className="w-full bg-primary text-on-primary hover:bg-primary/90 py-3 rounded font-label-caps text-[11px] uppercase tracking-widest transition-colors shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                            Acknowledge
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
