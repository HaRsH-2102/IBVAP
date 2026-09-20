import { useState, useEffect, createContext, useContext } from 'react';

const WsContext = createContext(null);

export const WsProvider = ({ children }) => {
    const [socket, setSocket] = useState(null);
    const [status, setStatus] = useState('DISCONNECTED');
    const [events, setEvents] = useState([]);
    
    useEffect(() => {
        const connect = () => {
            setStatus('CONNECTING');
            const ws = new WebSocket('ws://127.0.0.1:8000/ws/events');
            
            ws.onopen = () => {
                setStatus('CONNECTED');
                setSocket(ws);
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'ping' || data.type === 'pong' || data.type === 'SYSTEM_READY') return;
                    setEvents(prev => [data, ...prev].slice(0, 50));
                } catch (e) {
                    console.error("WS Message Error", e);
                }
            };
            
            ws.onclose = () => {
                setStatus('DISCONNECTED');
                setSocket(null);
                setTimeout(connect, 3000); // Reconnect loop
            };
        };
        
        connect();
        
        return () => {
            if (socket) socket.close();
        };
    }, []);

    return (
        <WsContext.Provider value={{ status, events }}>
            {children}
        </WsContext.Provider>
    );
};

export const useWs = () => useContext(WsContext);
