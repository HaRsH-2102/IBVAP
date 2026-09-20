import { useState, useEffect } from 'react';
import { analyticsApi } from '../api/client';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

export default function Analytics() {
    const [summary, setSummary] = useState(null);
    const [trends, setTrends] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            const [sumRes, trnRes] = await Promise.all([
                analyticsApi.summary(),
                analyticsApi.trends()
            ]);
            
            if (sumRes.ok) setSummary(await sumRes.json());
            if (trnRes.ok) setTrends(await trnRes.json());
        } catch (e) {
            console.error("Failed to fetch analytics", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // Auto-refresh every 30 seconds
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="h-full flex flex-col bg-surface-container-lowest p-6 justify-center items-center">
                <span className="material-symbols-outlined animate-spin text-[48px] text-primary mb-6 opacity-80">sync</span>
                <p className="font-label-caps tracking-widest text-primary uppercase text-[11px]">Loading Analytics Engine...</p>
            </div>
        );
    }

    if (!summary || summary.total_events === 0) {
        return (
            <div className="h-full flex flex-col bg-surface-container-lowest p-6 justify-center items-center">
                <div className="tech-panel p-16 text-center bg-surface border border-primary/30 max-w-lg shadow-[0_0_30px_rgba(0,240,255,0.1)]">
                    <span className="material-symbols-outlined text-[64px] text-primary/40 mb-6 block">monitoring</span>
                    <h2 className="font-display-lg text-2xl font-light text-on-surface mb-4 tracking-wide">No Events Recorded</h2>
                    <p className="font-data-mono text-[11px] text-on-surface-variant uppercase tracking-widest leading-relaxed">
                        The analytics engine relies on real security events. Start a surveillance session in Live Validation to begin gathering data.
                    </p>
                </div>
            </div>
        );
    }

    // Premium Chart Colors
    const COLORS = ['#00f0ff', '#00ffa6', '#ff3333', '#b366ff', '#ff9900'];

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-8 gap-8 overflow-auto custom-scrollbar">
            {/* Header */}
            <div className="flex justify-between items-center shrink-0 tech-panel p-6 bg-surface shadow-md">
                <div className="flex flex-col gap-2">
                    <h1 className="font-display-lg text-2xl font-light text-on-surface tracking-wide flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary text-[28px]">monitoring</span>
                        Security Analytics
                    </h1>
                    <p className="font-data-mono text-[11px] text-on-surface-variant uppercase tracking-widest">Real-time metrics derived from actual detection events.</p>
                </div>
                <button onClick={fetchData} className="px-5 py-2.5 bg-surface-variant border border-outline-variant/50 hover:border-primary text-on-surface hover:text-primary rounded font-label-caps text-[10px] uppercase tracking-widest transition-colors flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px]">refresh</span>
                    Manual Refresh
                </button>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 shrink-0">
                <KpiCard title="Total Events" value={summary.total_events} icon="local_police" color="text-primary" />
                <KpiCard title="Active Incidents" value={summary.active_incidents} icon="warning" color="text-[#ff3333]" alert={summary.active_incidents > 0} />
                <KpiCard title="Intrusions" value={summary.intrusions} icon="security" color="text-[#ff3333]" />
                <KpiCard title="Fence Crossings" value={summary.fence_crossings} icon="polyline" color="text-[#ff9900]" />
                <KpiCard title="Loitering" value={summary.loitering} icon="schedule" color="text-[#ff9900]" />
                <KpiCard title="Evidence Captured" value={summary.evidence_captured} icon="imagesmode" color="text-secondary" />
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-[450px]">
                
                {/* Time Series Chart */}
                <div className="lg:col-span-2 tech-panel bg-surface p-6 flex flex-col shadow-md">
                    <h3 className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest mb-6 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-primary rounded-full"></span>
                        Event Volume (Last 24 Hours)
                    </h3>
                    <div className="flex-1 min-h-[250px] bg-surface-dim p-4 border border-outline-variant/30 rounded">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={trends?.over_time || []} margin={{ top: 5, right: 20, bottom: 5, left: -20 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.2} vertical={false} />
                                <XAxis 
                                    dataKey="hour" 
                                    stroke="var(--color-outline-variant)" 
                                    tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 10, fontFamily: 'monospace' }}
                                    tickFormatter={(val) => {
                                        const d = new Date(val);
                                        return `${d.getHours()}:00`;
                                    }}
                                />
                                <YAxis stroke="var(--color-outline-variant)" tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 10, fontFamily: 'monospace' }} />
                                <Tooltip 
                                    contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-outline-variant)', color: '#fff', fontSize: 12, fontFamily: 'monospace', textTransform: 'uppercase' }}
                                    labelFormatter={(val) => new Date(val).toLocaleString()}
                                />
                                <Line type="monotone" dataKey="count" stroke="#00f0ff" strokeWidth={2} dot={{ r: 3, fill: '#00f0ff' }} activeDot={{ r: 6, fill: '#00ffa6', stroke: '#000' }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Event Types Donut */}
                <div className="tech-panel bg-surface p-6 flex flex-col shadow-md">
                    <h3 className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest mb-6 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-secondary rounded-full"></span>
                        Events by Type
                    </h3>
                    <div className="flex-1 min-h-[250px] relative flex flex-col bg-surface-dim p-4 border border-outline-variant/30 rounded">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={trends?.by_type || []}
                                    cx="50%" cy="45%"
                                    innerRadius={60} outerRadius={90}
                                    paddingAngle={2}
                                    dataKey="count"
                                    nameKey="type"
                                >
                                    {(trends?.by_type || []).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-outline-variant)', color: '#fff', fontSize: 12, fontFamily: 'monospace', textTransform: 'uppercase' }} />
                            </PieChart>
                        </ResponsiveContainer>
                        {/* Custom Legend */}
                        <div className="flex flex-wrap justify-center gap-4 mt-auto pt-4 border-t border-outline-variant/30">
                            {(trends?.by_type || []).map((entry, index) => (
                                <div key={entry.type} className="flex items-center gap-2 text-[10px] font-data-mono text-on-surface tracking-widest uppercase">
                                    <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLORS[index % COLORS.length] }}></div>
                                    {entry.type} ({entry.count})
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Object Class Distribution */}
                <div className="tech-panel bg-surface p-6 flex flex-col shadow-md">
                    <h3 className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest mb-6 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-[#b366ff] rounded-full"></span>
                        Person vs Vehicle
                    </h3>
                    <div className="flex-1 min-h-[200px] bg-surface-dim p-4 border border-outline-variant/30 rounded">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={trends?.by_class || []} layout="vertical" margin={{ top: 10, right: 20, bottom: 0, left: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.2} horizontal={false} />
                                <XAxis type="number" stroke="var(--color-outline-variant)" tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 10, fontFamily: 'monospace' }} />
                                <YAxis dataKey="class" type="category" stroke="var(--color-outline-variant)" tick={{ fill: 'var(--color-on-surface)', fontSize: 11, fontFamily: 'monospace', textTransform: 'uppercase', letterSpacing: '0.1em' }} />
                                <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-outline-variant)', color: '#fff', fontSize: 12, fontFamily: 'monospace', textTransform: 'uppercase' }} />
                                <Bar dataKey="count" fill="#b366ff" radius={[0, 4, 4, 0]} barSize={24} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Events by Camera */}
                <div className="lg:col-span-2 tech-panel bg-surface p-6 flex flex-col shadow-md">
                    <h3 className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest mb-6 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-[#ff9900] rounded-full"></span>
                        Events by Video Source
                    </h3>
                    <div className="flex-1 min-h-[200px] bg-surface-dim p-4 border border-outline-variant/30 rounded">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={trends?.by_camera || []} margin={{ top: 10, right: 20, bottom: 0, left: -10 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.2} vertical={false} />
                                <XAxis dataKey="camera" stroke="var(--color-outline-variant)" tick={{ fill: 'var(--color-on-surface)', fontSize: 10, fontFamily: 'monospace', letterSpacing: '0.1em' }} />
                                <YAxis stroke="var(--color-outline-variant)" tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 10, fontFamily: 'monospace' }} />
                                <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-outline-variant)', color: '#fff', fontSize: 12, fontFamily: 'monospace', textTransform: 'uppercase' }} />
                                <Bar dataKey="count" fill="#ff9900" radius={[4, 4, 0, 0]} barSize={40} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

            </div>
        </div>
    );
}

function KpiCard({ title, value, icon, color, alert }) {
    return (
        <div className={`tech-panel p-5 bg-surface flex flex-col justify-between shadow-md border-l-4 transition-colors ${alert ? 'border-l-[#ff3333] shadow-[inset_0_0_20px_rgba(255,51,51,0.1)]' : 'border-l-primary/30 hover:border-l-primary'}`}>
            <div className="flex justify-between items-start mb-4">
                <span className={`font-label-caps text-[11px] uppercase tracking-widest ${alert ? 'text-[#ff3333]' : 'text-outline-variant'}`}>{title}</span>
                <span className={`material-symbols-outlined text-[20px] ${alert ? 'text-[#ff3333]' : color}`}>{icon}</span>
            </div>
            <div className={`text-3xl font-data-mono font-bold tracking-widest ${alert ? 'text-[#ff3333]' : 'text-on-surface'}`}>
                {value.toLocaleString()}
            </div>
        </div>
    );
}
