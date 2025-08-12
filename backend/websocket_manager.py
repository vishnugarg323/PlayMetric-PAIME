from typing import Dict, List
from fastapi import WebSocket
import json

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.session_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Connect a new WebSocket client"""
        await websocket.accept()
        if client_id:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = []
            self.active_connections[client_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, client_id: str = None):
        """Disconnect a WebSocket client"""
        if client_id and client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        await websocket.send_text(message)
    
    async def broadcast(self, message: str, client_id: str = None):
        """Broadcast message to all connections or specific client"""
        if client_id and client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_text(message)
        else:
            for connections in self.active_connections.values():
                for connection in connections:
                    await connection.send_text(message)
    
    async def send_json(self, data: dict, client_id: str = None):
        """Send JSON data"""
        message = json.dumps(data)
        await self.broadcast(message, client_id)