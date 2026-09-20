import React, { useState } from 'react';
import { eventApi } from '../api/client';

const DemoOperator = () => {
    const [eventId, setEventId] = useState('');
    const [plateText, setPlateText] = useState('');
    const [status, setStatus] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setStatus('');
        setError('');
        
        if (!eventId.trim() || !plateText.trim()) {
            setError("Both fields are required.");
            return;
        }

        try {
            const res = await eventApi.overridePlate(eventId.trim(), {
                plate_text: plateText.trim().toUpperCase()
            });
            
            if (!res.ok) {
                let errorDetail = "An error occurred during plate override";
                try {
                    const errorData = await res.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (e) {}
                setError(errorDetail);
                return;
            }
            
            setStatus(`Successfully overridden plate for Event ID: ${eventId}`);
            setPlateText('');
        } catch (err) {
            setError("Network error occurred during plate override");
        }
    };

    return (
        <div className="p-8 max-w-2xl mx-auto h-full overflow-y-auto">
            <h1 className="text-2xl font-bold tracking-widest text-on-surface mb-6 uppercase">Internal Demo Operator Panel</h1>
            <p className="text-outline-variant mb-8 text-sm">
                This panel is strictly for SIH Demo manual annotation. It associates a plate with a SecurityEvent without destroying the original AI metadata.
            </p>

            <form onSubmit={handleSubmit} className="bg-surface-dim border border-outline-variant/30 rounded p-6 flex flex-col gap-6">
                <div className="flex flex-col gap-2">
                    <label className="text-[12px] uppercase tracking-widest font-label-caps text-on-surface-variant">Security Event ID</label>
                    <input 
                        type="text" 
                        value={eventId}
                        onChange={(e) => setEventId(e.target.value)}
                        placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                        className="bg-background border border-outline-variant/50 rounded px-4 py-2 text-on-surface font-data-mono outline-none focus:border-primary transition-colors"
                    />
                </div>

                <div className="flex flex-col gap-2">
                    <label className="text-[12px] uppercase tracking-widest font-label-caps text-on-surface-variant">Vehicle Registration (Plate)</label>
                    <input 
                        type="text" 
                        value={plateText}
                        onChange={(e) => setPlateText(e.target.value)}
                        placeholder="e.g. MH12AB1234"
                        className="bg-background border border-outline-variant/50 rounded px-4 py-2 text-on-surface font-data-mono uppercase outline-none focus:border-primary transition-colors"
                    />
                </div>

                <button 
                    type="submit"
                    className="bg-primary text-black font-bold tracking-widest uppercase text-sm py-3 rounded hover:brightness-110 transition-all mt-4"
                >
                    Associate Plate
                </button>

                {error && (
                    <div className="bg-error/20 border border-error/50 text-error px-4 py-3 rounded text-sm tracking-widest">
                        {error}
                    </div>
                )}
                
                {status && (
                    <div className="bg-secondary/20 border border-secondary/50 text-secondary px-4 py-3 rounded text-sm tracking-widest">
                        {status}
                    </div>
                )}
            </form>
        </div>
    );
};

export default DemoOperator;
