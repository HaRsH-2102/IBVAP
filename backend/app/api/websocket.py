import json
import asyncio
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.logging_config import get_logger

router = APIRouter(tags=["websocket"])
logger = get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WS message: {e}")
                dead_connections.append(connection)
                
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket) -> None:
    client_host = websocket.client.host if websocket.client else "unknown"
    await manager.connect(websocket)
    logger.info("WebSocket client connected", extra={"client": client_host})

    # Send system-ready handshake
    await websocket.send_json({
        "type": "SYSTEM_READY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "IBVAP WebSocket boundary established."
    })

    try:
        while True:
            # Keep connection alive; echo ping messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except json.JSONDecodeError:
                pass  # Ignore malformed messages

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected", extra={"client": client_host})

# Background task for sending dummy periodic TRACK_SUMMARY_UPDATED and polling for new alerts
from app.infrastructure.database import SQLiteDatabase
import sqlite3

async def periodic_track_updates():
    db = SQLiteDatabase()
    last_seen_alert_time = datetime.now(timezone.utc).isoformat()
    
    while True:
        await asyncio.sleep(1.0)
        if not manager.active_connections:
            continue
            
        # Broadcast track summary
        update = {
            "type": "TRACK_SUMMARY_UPDATED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "camera_id": "cam_test_01",
            "tracks": []
        }
        await manager.broadcast(update)
        
        # Poll for new alerts
        try:
            conn = db.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts WHERE created_at > ? ORDER BY created_at ASC", (last_seen_alert_time,))
            new_alerts = cursor.fetchall()
            
            for row in new_alerts:
                alert_dict = dict(row)
                await manager.broadcast({
                    "type": "NEW_ALERT",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "alert": alert_dict
                })
                last_seen_alert_time = alert_dict["created_at"]
        except Exception as e:
            logger.error(f"Error polling alerts: {e}")
