import { NavLink, Outlet } from 'react-router-dom';
import { useWs } from './api/ws';
import { useEffect, useState } from 'react';
import { systemApi } from './api/client';

export default function Layout() {
    const { status, events } = useWs();
    const [currentTime, setCurrentTime] = useState(new Date());
    const [systemHealth, setSystemHealth] = useState(null);

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        const fetchHealth = async () => {
            try {
                const res = await systemApi.health();
                if (res.ok) {
                    setSystemHealth('ONLINE');
                } else {
                    setSystemHealth('ERROR');
                }
            } catch (error) {
                setSystemHealth('OFFLINE');
            }
        };
        fetchHealth();
        const healthTimer = setInterval(fetchHealth, 30000);
        return () => clearInterval(healthTimer);
    }, []);

    const navGroups = [
        {
            title: "COMMAND",
            items: [
                { path: '/', icon: 'dashboard', label: 'Command Center' },
                { path: '/live', icon: 'videocam', label: 'Live Surveillance' },
                { path: '/live-validation', icon: 'verified', label: 'Live Validation Demo' },
            ]
        },
        {
            title: "MONITORING",
            items: [
                { path: '/cameras', icon: 'nest_cam_iq_outdoor', label: 'Cameras' },
                { path: '/alerts', icon: 'emergency', label: 'Active Incidents' },
                { path: '/events', icon: 'history', label: 'Event History' },
            ]
        },
        {
            title: "INTELLIGENCE",
            items: [
                { path: '/analytics', icon: 'monitoring', label: 'Analytics' },
                { path: '/anpr', icon: 'directions_car', label: 'ANPR Intelligence' },
                { path: '/evidence', icon: 'image', label: 'Evidence Explorer' },
            ]
        },
        {
            title: "CONFIGURATION",
            items: [
                { path: '/zones', icon: 'share_location', label: 'Zones / Tripwires' },
                { path: '/health', icon: 'ecg', label: 'System Health' },
                { path: '/settings', icon: 'settings', label: 'Settings' },
            ]
        }
    ];

    const activeAlertsCount = events.filter(e => e.type === 'NEW_ALERT' && e.alert?.status === 'OPEN').length; // Simplistic count based on WS

    return (
        <div className="bg-background text-on-surface font-body-base h-screen overflow-hidden flex selection:bg-primary/30 selection:text-primary">
            {/* SideNavBar */}
            <nav className="fixed left-0 top-0 h-screen w-[260px] border-r border-outline-variant bg-surface flex flex-col py-6 z-20 shadow-[4px_0_24px_rgba(0,0,0,0.5)]">
                <div className="px-6 mb-8 flex items-center gap-3">
                    <div className="w-8 h-8 bg-primary/10 rounded flex items-center justify-center border border-primary/30 shadow-[0_0_10px_rgba(0,240,255,0.2)]">
                        <span className="material-symbols-outlined text-[20px] text-primary">shield</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="font-display-lg text-lg font-bold text-primary tracking-widest leading-none">IBVAP</span>
                        <span className="font-label-caps text-[10px] text-on-surface-variant uppercase mt-1 tracking-widest">Command Center</span>
                    </div>
                </div>
                
                <div className="flex-1 overflow-y-auto px-4 custom-scrollbar">
                    {navGroups.map((group, gIdx) => (
                        <div key={gIdx} className="mb-6">
                            <h3 className="px-2 mb-2 font-label-caps text-[10px] text-outline-variant uppercase tracking-widest">{group.title}</h3>
                            <ul className="flex flex-col gap-1">
                                {group.items.map((item) => (
                                    <li key={item.path}>
                                        <NavLink
                                            to={item.path}
                                            className={({ isActive }) =>
                                                `w-full flex items-center gap-3 px-3 py-2 rounded font-body-sm transition-all duration-200 ${
                                                    isActive
                                                        ? 'text-primary bg-primary/10 font-medium shadow-[inset_2px_0_0_0_rgba(0,240,255,1)]'
                                                        : 'text-on-surface-variant hover:bg-surface-variant hover:text-on-surface'
                                                }`
                                            }
                                        >
                                            <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
                                            {item.label}
                                        </NavLink>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>

                <div className="px-6 pt-4 mt-auto border-t border-outline-variant/50 bg-surface/80 backdrop-blur">
                    <div className="flex items-center justify-between text-[11px] font-data-mono mb-2">
                        <span className="text-outline-variant">DATALINK:</span>
                        <span className={status === 'CONNECTED' ? 'text-secondary font-bold' : 'text-error font-bold'}>{status}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] font-data-mono">
                        <span className="text-outline-variant">CORE API:</span>
                        <span className={systemHealth === 'ONLINE' ? 'text-secondary font-bold' : 'text-error font-bold animate-pulse'}>{systemHealth || 'CONNECTING'}</span>
                    </div>
                </div>
            </nav>

            {/* Main Content Area */}
            <div className="ml-[260px] flex-1 flex flex-col h-screen">
                {/* TopAppBar */}
                <header className="h-14 border-b border-outline-variant bg-surface/95 backdrop-blur flex justify-between items-center px-6 z-10 shrink-0">
                    <div className="font-label-caps text-[12px] text-outline-variant uppercase tracking-widest flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_5px_rgba(0,255,166,0.5)]"></span>
                        Operational Readiness: Optimal
                    </div>
                    
                    <div className="flex items-center gap-6">
                        {activeAlertsCount > 0 && (
                            <div className="flex items-center gap-2 bg-[#ff3333]/10 text-[#ff3333] px-3 py-1 rounded border border-[#ff3333]/30 font-data-mono text-xs animate-pulse shadow-[0_0_10px_rgba(255,51,51,0.2)]">
                                <span className="material-symbols-outlined text-[16px]">warning</span>
                                {activeAlertsCount} ACTIVE INCIDENTS
                            </div>
                        )}
                        <div className="flex items-center gap-2 text-outline-variant font-data-mono text-xs bg-surface-dim px-3 py-1 rounded border border-outline-variant/50">
                            <span className="material-symbols-outlined text-[14px]">schedule</span>
                            <span className="text-on-surface">{currentTime.toISOString().substring(11, 19)}</span> UTC
                        </div>
                    </div>
                </header>

                {/* Page Content */}
                <main className="flex-1 overflow-y-auto bg-surface-container-lowest relative">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
