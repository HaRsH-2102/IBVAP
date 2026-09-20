import { useState, useEffect } from 'react';

const ZONE_FILL = 'rgba(239,68,68,0.2)';
const ZONE_STROKE = '#EF4444';
const FENCE_STROKE = '#06B6D4';
const SELECTED_STROKE = '#FBBF24';
const VERTEX_RADIUS = 0.008;

export default function ZoneDrawingOverlay({ 
    mode, 
    onModeChange, 
    zones, 
    setZones, 
    lines, 
    setLines,
    onSaveZone,
    onSaveLine,
    onUpdateZone,
    onUpdateLine,
    selectedId,
    setSelectedId,
    setSelectedType,
    currentPoints,
    setCurrentPoints
}) {
    const [cursorPt, setCursorPt] = useState(null);
    const [dragInfo, setDragInfo] = useState(null);

    const isDrawing = mode === 'DRAW_ZONE' || mode === 'DRAW_FENCE';
    const isEditing = mode === 'EDIT';

    useEffect(() => {
        setCurrentPoints([]);
        setCursorPt(null);
        setDragInfo(null);
    }, [mode]);

    const getCoords = (e) => {
        const svg = e.currentTarget;
        const svgElement = svg.tagName === 'svg' ? svg : svg.ownerSVGElement;
        if (!svgElement) return null;
        
        const rect = svgElement.getBoundingClientRect();
        const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
        return { x, y };
    };

    const handlePointerMove = (e) => {
        const pt = getCoords(e);
        if (!pt) return;

        if (isDrawing) {
            setCursorPt(pt);
        } else if (isEditing && dragInfo) {
            const { type, id, vertexIdx } = dragInfo;
            if (type === 'zone') {
                setZones(prev => prev.map(z => {
                    if (z.zone_id === id) {
                        const newGeom = [...z.geometry];
                        newGeom[vertexIdx] = pt;
                        return { ...z, geometry: newGeom };
                    }
                    return z;
                }));
            } else if (type === 'line') {
                setLines(prev => prev.map(l => {
                    if (l.line_id === id) {
                        const newPts = [...l.points];
                        newPts[vertexIdx] = pt;
                        return { ...l, points: newPts };
                    }
                    return l;
                }));
            }
        }
    };

    const handlePointerUp = (e) => {
        if (isEditing && dragInfo) {
            const { type, id } = dragInfo;
            if (type === 'zone') {
                const zone = zones.find(z => z.zone_id === id);
                if (zone) onUpdateZone(id, { geometry: zone.geometry });
            } else if (type === 'line') {
                const line = lines.find(l => l.line_id === id);
                if (line) onUpdateLine(id, { points: line.points });
            }
            setDragInfo(null);
        }
    };

    const handleClick = (e) => {
        if (isEditing && dragInfo) return;

        if (isDrawing) {
            const pt = getCoords(e);
            if (pt) setCurrentPoints(prev => [...prev, pt]);
        } else if (isEditing) {
            if (e.target.tagName === 'svg') {
                setSelectedId(null);
                setSelectedType(null);
            }
        }
    };

    const handleContextMenu = (e) => {
        e.preventDefault();
        if (isDrawing) handleFinishDrawing();
    };

    const handleFinishDrawing = () => {
        if (mode === 'DRAW_ZONE' && currentPoints.length >= 3) {
            onSaveZone(currentPoints);
        } else if (mode === 'DRAW_FENCE' && currentPoints.length >= 2) {
            onSaveLine(currentPoints);
        } else {
            // Cancel if not enough points when right clicking
            setCurrentPoints([]);
            onModeChange('IDLE');
        }
        setCursorPt(null);
    };

    const currentPath = currentPoints.map(p => `${p.x},${p.y}`).join(' ');
    
    return (
        <svg
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
            className="absolute inset-0 w-full h-full"
            style={{
                zIndex: (isDrawing || isEditing) ? 50 : 10,
                pointerEvents: (isDrawing || isEditing) ? 'all' : 'none',
                cursor: isDrawing ? 'crosshair' : 'default',
            }}
            onClick={handleClick}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onContextMenu={handleContextMenu}
        >
            {zones.map(z => {
                const pts = z.geometry.map(p => `${p.x},${p.y}`).join(' ');
                const isSelected = selectedId === z.zone_id;
                return (
                    <g key={z.zone_id}>
                        <polygon
                            points={pts}
                            fill={ZONE_FILL}
                            stroke={isSelected ? SELECTED_STROKE : ZONE_STROKE}
                            strokeWidth={isSelected ? 0.004 : 0.002}
                            onClick={(e) => {
                                if (isEditing) {
                                    e.stopPropagation();
                                    setSelectedId(z.zone_id);
                                    setSelectedType('zone');
                                }
                            }}
                            style={{ cursor: isEditing ? 'pointer' : 'default' }}
                        />
                        {isEditing && isSelected && z.geometry.map((p, i) => (
                            <circle
                                key={i}
                                cx={p.x} cy={p.y} r={VERTEX_RADIUS}
                                fill="white" stroke="black" strokeWidth="0.001"
                                style={{ cursor: 'grab' }}
                                onPointerDown={(e) => {
                                    e.stopPropagation();
                                    setDragInfo({ type: 'zone', id: z.zone_id, vertexIdx: i });
                                }}
                            />
                        ))}
                    </g>
                );
            })}

            {lines.map(l => {
                const pts = l.points.map(p => `${p.x},${p.y}`).join(' ');
                const isSelected = selectedId === l.line_id;
                return (
                    <g key={l.line_id}>
                        <polyline
                            points={pts}
                            fill="none"
                            stroke={isSelected ? SELECTED_STROKE : FENCE_STROKE}
                            strokeWidth={isSelected ? 0.004 : 0.003}
                            onClick={(e) => {
                                if (isEditing) {
                                    e.stopPropagation();
                                    setSelectedId(l.line_id);
                                    setSelectedType('line');
                                }
                            }}
                            style={{ cursor: isEditing ? 'pointer' : 'default' }}
                        />
                        {isEditing && isSelected && l.points.map((p, i) => (
                            <circle
                                key={i}
                                cx={p.x} cy={p.y} r={VERTEX_RADIUS}
                                fill="white" stroke="black" strokeWidth="0.001"
                                style={{ cursor: 'grab' }}
                                onPointerDown={(e) => {
                                    e.stopPropagation();
                                    setDragInfo({ type: 'line', id: l.line_id, vertexIdx: i });
                                }}
                            />
                        ))}
                    </g>
                );
            })}

            {isDrawing && currentPoints.length > 0 && (
                <g>
                    {mode === 'DRAW_ZONE' ? (
                        <polygon
                            points={`${currentPath} ${cursorPt ? `${cursorPt.x},${cursorPt.y}` : ''}`}
                            fill={ZONE_FILL}
                            stroke={ZONE_STROKE}
                            strokeWidth="0.002"
                            strokeDasharray="0.01 0.005"
                        />
                    ) : (
                        <polyline
                            points={`${currentPath} ${cursorPt ? `${cursorPt.x},${cursorPt.y}` : ''}`}
                            fill="none"
                            stroke={FENCE_STROKE}
                            strokeWidth="0.003"
                            strokeDasharray="0.01 0.005"
                        />
                    )}
                    {currentPoints.map((p, i) => (
                        <circle key={i} cx={p.x} cy={p.y} r={VERTEX_RADIUS} fill="white" />
                    ))}
                </g>
            )}
        </svg>
    );
}
