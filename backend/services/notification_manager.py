"""
WebSocket-based notification manager for real-time updates.
"""
import json
import logging
import asyncio
import time
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from dependencies import profile_manager
from services.email_service import email_service
import config

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
    """Service for sending different types of notifications.

    Note: In-app WebSocket notifications are immediate by design. The
    `interaction_preferences.notification_frequency` is reserved for future
    external channels (email/SMS) and is not applied here.
    """
    
    @staticmethod
    async def notify_new_research(user_id: str, topic_id: str, result_id: str, topic_name: str = None):
        """Notify user about new research results."""
        message = {
            "type": "new_research",
            "data": {
                "topic_id": topic_id,
                "result_id": result_id,
                "topic_name": topic_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        logger.info(f"📡 NotificationService: Sending new research notification to user {user_id}")
        await connection_manager.send_to_user(user_id, message)

        # Also send email notification if the user has an email
        try:
            user_data = profile_manager.get_user(user_id)
            email = (user_data or {}).get("metadata", {}).get("email")
            if email:
                subject = "New research finding available"
                topic_part = f" on '{topic_name}'" if topic_name else ""
                link = f"{config.FRONTEND_URL}/research-results?user={user_id}&topic={topic_id}"
                text_body = (
                    f"Hello,\n\nA new background research finding{topic_part} is available.\n"
                    f"Finding ID: {result_id}\n"
                    f"Open the app to review: {link}\n\n"
                    f"— AI Research Assistant"
                )
                html_body = (
                    f"<div style=\"font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #111827;\">"
                    f"  <div style=\"max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden;\">"
                    f"    <div style=\"padding: 20px 24px; background: linear-gradient(135deg,#f0f7ff,#eefdf5); border-bottom: 1px solid #e5e7eb;\">"
                    f"      <h2 style=\"margin: 0; font-size: 18px; color: #111827;\">New research finding{topic_part}</h2>"
                    f"      <p style=\"margin: 4px 0 0; color: #6b7280; font-size: 14px;\">Your background research just finished processing.</p>"
                    f"    </div>"
                    f"    <div style=\"padding: 20px 24px;\">"
                    f"      <p style=\"margin: 0 0 12px;\"><strong>Finding ID:</strong> {result_id}</p>"
                    f"      <a href=\"{link}\" style=\"display: inline-block; padding: 10px 14px; background: #4f46e5; color: white; text-decoration: none; border-radius: 8px;\">Open research</a>"
                    f"    </div>"
                    f"    <div style=\"padding: 12px 24px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px;\">"
                    f"      <p style=\"margin: 0;\">You received this because you initiated background research.</p>"
                    f"    </div>"
                    f"  </div>"
                    f"</div>"
                )
                email_service.send_email(email, subject, text_body, html_body)
        except Exception as exc:
            logger.warning(f"📧 Skipping email notification for new research due to error: {exc}")
    
    @staticmethod
    async def notify_research_complete(user_id: str, topic_id: str, results_count: int, topic_name: str = None):
        """Notify user when a research cycle completes."""
        message = {
            "type": "research_complete",
            "data": {
                "topic_id": topic_id,
                "results_count": results_count,
                "topic_name": topic_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        await connection_manager.send_to_user(user_id, message)

        # Also send email notification if the user has an email
        try:
            user_data = profile_manager.get_user(user_id)
            email = (user_data or {}).get("metadata", {}).get("email")
            if email:
                subject = "Research update completed"
                topic_part = f" for '{topic_name}'" if topic_name else ""
                link = f"{config.FRONTEND_URL}/research-results?user={user_id}"
                text_body = (
                    f"Hello,\n\nYour background research{topic_part} has completed.\n"
                    f"New findings: {results_count}.\n"
                    f"Open the app to review: {link}\n\n"
                    f"— AI Research Assistant"
                )
                html_body = (
                    f"<div style=\"font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #111827;\">"
                    f"  <div style=\"max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden;\">"
                    f"    <div style=\"padding: 20px 24px; background: linear-gradient(135deg,#f0f7ff,#eefdf5); border-bottom: 1px solid #e5e7eb;\">"
                    f"      <h2 style=\"margin: 0; font-size: 18px; color: #111827;\">Research completed{topic_part}</h2>"
                    f"      <p style=\"margin: 4px 0 0; color: #6b7280; font-size: 14px;\">We saved your latest findings.</p>"
                    f"    </div>"
                    f"    <div style=\"padding: 20px 24px;\">"
                    f"      <p style=\"margin: 0 0 12px;\"><strong>New findings:</strong> {results_count}</p>"
                    f"      <a href=\"{link}\" style=\"display: inline-block; padding: 10px 14px; background: #4f46e5; color: white; text-decoration: none; border-radius: 8px;\">Open research</a>"
                    f"    </div>"
                    f"    <div style=\"padding: 12px 24px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px;\">"
                    f"      <p style=\"margin: 0;\">You received this because you initiated background research.</p>"
                    f"    </div>"
                    f"  </div>"
                    f"</div>"
                )
                email_service.send_email(email, subject, text_body, html_body)
        except Exception as exc:
            logger.warning(f"📧 Skipping email notification due to error: {exc}")
    
    @staticmethod
    async def notify_system_status(status: str, details: dict = None):
        """Broadcast system status updates to all users."""
        message = {
            "type": "system_status",
            "data": {
                "status": status,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        await connection_manager.broadcast_to_all(message)


# Convenience instance
notification_service = NotificationService()