"""
WebSocket Manager for Real-Time Updates
Provides live dashboard updates for screenshots, metrics, logs, etc.
"""

import asyncio
import logging
from typing import Dict, Set
from datetime import datetime
import socketio
import json

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*',
            logger=False,
            engineio_logger=False
        )
        self.connected_clients: Set[str] = set()
        self.session_subscribers: Dict[str, Set[str]] = {}  # session_id -> set of client sids
        
        self._register_events()
    
    def _register_events(self):
        """Register Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection"""
            self.connected_clients.add(sid)
            logger.info(f"Client connected: {sid}")
            await self.sio.emit('connected', {'client_id': sid}, room=sid)
        
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            self.connected_clients.discard(sid)
            # Remove from all session subscriptions
            for session_id in list(self.session_subscribers.keys()):
                self.session_subscribers[session_id].discard(sid)
                if not self.session_subscribers[session_id]:
                    del self.session_subscribers[session_id]
            logger.info(f"Client disconnected: {sid}")
        
        @self.sio.event
        async def subscribe_session(sid, data):
            """Subscribe to session updates"""
            session_id = data.get('session_id')
            if session_id:
                if session_id not in self.session_subscribers:
                    self.session_subscribers[session_id] = set()
                self.session_subscribers[session_id].add(sid)
                logger.info(f"Client {sid} subscribed to session {session_id}")
                await self.sio.emit('subscribed', {'session_id': session_id}, room=sid)
        
        @self.sio.event
        async def unsubscribe_session(sid, data):
            """Unsubscribe from session updates"""
            session_id = data.get('session_id')
            if session_id and session_id in self.session_subscribers:
                self.session_subscribers[session_id].discard(sid)
                logger.info(f"Client {sid} unsubscribed from session {session_id}")
                await self.sio.emit('unsubscribed', {'session_id': session_id}, room=sid)
    
    def get_asgi_app(self, other_asgi_app=None):
        """Get ASGI app for mounting or wrapping.

        If `other_asgi_app` is provided, return an ASGI app that will
        delegate non-socket.io requests to the provided ASGI application.
        This is the recommended way to run Socket.IO together with FastAPI
        so both websocket and HTTP routes are handled correctly.
        """
        return socketio.ASGIApp(self.sio, other_asgi_app=other_asgi_app, socketio_path='/socket.io')
    
    async def broadcast_screenshot(self, session_id: str, screenshot_data: Dict):
        """Broadcast screenshot update"""
        if session_id in self.session_subscribers:
            for sid in self.session_subscribers[session_id]:
                await self.sio.emit(
                    f'screenshot:{session_id}',
                    screenshot_data,
                    room=sid
                )
    
    async def broadcast_metrics(self, session_id: str, metrics: Dict):
        """Broadcast performance metrics"""
        if session_id in self.session_subscribers:
            for sid in self.session_subscribers[session_id]:
                await self.sio.emit(
                    f'metrics:{session_id}',
                    {
                        'timestamp': datetime.utcnow().isoformat(),
                        **metrics
                    },
                    room=sid
                )
    
    async def broadcast_bug_detected(self, bug_data: Dict):
        """Broadcast bug detection to all clients"""
        await self.sio.emit('bug:detected', bug_data)
    
    async def broadcast_crash_detected(self, crash_data: Dict):
        """Broadcast crash detection to all clients"""
        await self.sio.emit('crash:detected', crash_data)
    
    async def broadcast_session_update(self, session_id: str, update: Dict):
        """Broadcast session status update"""
        if session_id in self.session_subscribers:
            for sid in self.session_subscribers[session_id]:
                await self.sio.emit(
                    f'session:{session_id}',
                    update,
                    room=sid
                )
        
        # Also broadcast to all clients
        await self.sio.emit('session:update', {
            'session_id': session_id,
            **update
        })
    
    async def broadcast_log(self, session_id: str, log_entry: Dict):
        """Broadcast log entry"""
        if session_id in self.session_subscribers:
            for sid in self.session_subscribers[session_id]:
                await self.sio.emit(
                    f'log:{session_id}',
                    log_entry,
                    room=sid
                )
    
    async def broadcast_message(self, event: str, data: Dict):
        """Broadcast a generic message to all clients or specific session
        
        Args:
            event: Event name (e.g., 'session_123' or 'global_event')
            data: Data to broadcast
        """
        # Check if this is a session-specific event
        if event.startswith('session_'):
            session_id = event.replace('session_', '')
            if session_id in self.session_subscribers:
                for sid in self.session_subscribers[session_id]:
                    await self.sio.emit(event, data, room=sid)
        else:
            # Broadcast to all connected clients
            await self.sio.emit(event, data)
    
    async def get_stats(self) -> Dict:
        """Get WebSocket stats"""
        return {
            'connected_clients': len(self.connected_clients),
            'active_subscriptions': sum(len(subs) for subs in self.session_subscribers.values()),
            'sessions_with_subscribers': len(self.session_subscribers)
        }


# Singleton instance
_ws_manager: WebSocketManager = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create WebSocket manager instance"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
