"""
WebSocket-based notification manager for real-time updates.
"""
import json
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for notifications."""
    
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a WebSocket connection for a user."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"🔌 User {user_id} connected to notifications (total connections: {len(self.active_connections[user_id])})")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection for a user."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"🔌 User {user_id} disconnected from notifications")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a notification to all connections for a specific user."""
        if user_id not in self.active_connections:
            logger.info(f"📡 No active connections for user {user_id} (total users: {len(self.active_connections)})")
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections = self.active_connections[user_id].copy()
        disconnected_connections = []
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
                logger.debug(f"📡 Sent notification to user {user_id}: {message.get('type', 'unknown')}")
            except Exception as e:
                logger.warning(f"📡 Failed to send notification to user {user_id}: {e}")
                disconnected_connections.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.disconnect(connection, user_id)
    
    async def broadcast_to_all(self, message: dict):
        """Send a notification to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)
    
    def get_connection_count(self, user_id: Optional[str] = None) -> int:
        """Get the number of active connections."""
        if user_id:
            return len(self.active_connections.get(user_id, set()))
        return sum(len(connections) for connections in self.active_connections.values())


# Global connection manager instance
connection_manager = ConnectionManager()


class NotificationService:
    """Service for sending different types of notifications."""
    
    @staticmethod
    async def notify_new_research(user_id: str, topic_id: str, result_id: str, topic_name: str = None):
        """Notify user about new research results."""
        message = {
            "type": "new_research",
            "data": {
                "topic_id": topic_id,
                "result_id": result_id,
                "topic_name": topic_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        logger.info(f"📡 NotificationService: Sending new research notification to user {user_id}")
        await connection_manager.send_to_user(user_id, message)
    
    @staticmethod
    async def notify_research_complete(user_id: str, topic_id: str, results_count: int, topic_name: str = None):
        """Notify user when a research cycle completes."""
        message = {
            "type": "research_complete",
            "data": {
                "topic_id": topic_id,
                "results_count": results_count,
                "topic_name": topic_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await connection_manager.send_to_user(user_id, message)
    
    @staticmethod
    async def notify_system_status(status: str, details: dict = None):
        """Broadcast system status updates to all users."""
        message = {
            "type": "system_status",
            "data": {
                "status": status,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await connection_manager.broadcast_to_all(message)


# Convenience instance
notification_service = NotificationService()