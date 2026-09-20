import { useState, useEffect } from 'react';
import { eventApi } from '../api/client';
import { useWs } from '../api/ws';

export default function EventHistory() {
    const [events, setEvents] = useState([]);
    const [summary, setSummary] = useState(null);
    const { events: wsEvents } = useWs();

    const fetchEvents = async () => {
        try {
            const res = await eventApi.list({ limit: 100 });
            if (res.ok) setEvents(await res.json());
            
            const sumRes = await eventApi.summary();
            if (sumRes.ok) setSummary(await sumRes.json());
        } catch (e) {
            console.error("fetch events failed", e);
        }
    };

    useEffect(() => {
        fetchEvents();
    }, []);

    useEffect(() => {
        if (wsEvents.length > 0 && wsEvents[0].type === 'NEW_EVENT') {
            fetchEvents();
        }
    }, [wsEvents]);

    return (
        <div className="flex flex-col h-full bg-surface-container-lowest p-6 gap-6">
            <div className="flex justify-between items-center shrink-0">
                <h1 className="font-display-lg text-2xl font-light text-on-surface flex items-center gap-3 tracking-wide">
                    <span className="material-symbols-outlined text-primary text-[28px]">history</span> Event History
                </h1>
                <button onClick={fetchEvents} className="flex items-center gap-2 px-4 py-2 bg-surface-variant border border-outline-variant/50 text-on-surface hover:text-primary hover:border-primary rounded font-label-caps uppercase text-[10px] tracking-widest transition-colors">
                    <span className="material-symbols-outlined text-[16px]">refresh</span> Refresh Log
                </button>
            </div>

            {summary && (
                <div className="grid grid-cols-4 gap-6 shrink-0">
                    <div className="tech-panel p-5 bg-surface border-l-4 border-l-primary shadow-md flex flex-col gap-2">
                        <span className="font-label-caps text-outline-variant text-[11px] uppercase tracking-widest">Total Events</span>
                        <span className="font-data-mono text-3xl font-bold text-on-surface tracking-widest">{summary.total_events}</span>
                    </div>
                </div>
            )}

            <div className="flex-1 tech-panel bg-surface overflow-hidden flex flex-col min-h-0">
                <div className="px-6 py-4 border-b border-outline-variant/50 bg-surface-dim flex justify-between items-center shrink-0">
                    <span className="font-label-caps text-on-surface-variant uppercase text-[12px] tracking-widest">Event Log</span>
                </div>
                <div className="flex-1 overflow-auto bg-background custom-scrollbar">
                    <table className="w-full text-left font-data-mono text-[11px]">
                        <thead className="bg-surface-dim text-outline-variant sticky top-0 z-10 border-b border-outline-variant/50">
                            <tr>
                                <th className="px-6 py-4 font-medium tracking-widest uppercase">Timestamp</th>
                                <th className="px-6 py-4 font-medium tracking-widest uppercase">Event Type</th>
                                <th className="px-6 py-4 font-medium tracking-widest uppercase">Camera</th>
                                <th className="px-6 py-4 font-medium tracking-widest uppercase">Track ID</th>
                                <th className="px-6 py-4 font-medium tracking-widest uppercase text-right">Confidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            {events.map((e, i) => (
                                <tr key={e.event_id + i} className="border-b border-outline-variant/30 hover:bg-surface-variant transition-colors group">
                                    <td className="px-6 py-4 text-on-surface-variant tracking-widest group-hover:text-on-surface transition-colors">{new Date(e.timestamp).toISOString().replace('T', ' ').substring(0, 19)}</td>
                                    <td className="px-6 py-4 text-primary font-bold uppercase tracking-widest">{e.event_type}</td>
                                    <td className="px-6 py-4 text-on-surface-variant tracking-widest">{e.camera_id}</td>
                                    <td className="px-6 py-4 text-on-surface truncate max-w-[120px] tracking-widest">{e.track_id}</td>
                                    <td className="px-6 py-4 text-on-surface-variant tracking-widest text-right">{(e.confidence * 100).toFixed(1)}%</td>
                                </tr>
                            ))}
                            {events.length === 0 && (
                                <tr>
                                    <td colSpan="5" className="p-12 text-center text-outline-variant font-data-mono tracking-widest uppercase">
                                        <span className="material-symbols-outlined text-[48px] opacity-20 block mb-4">history</span>
                                        NO EVENTS LOGGED
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
