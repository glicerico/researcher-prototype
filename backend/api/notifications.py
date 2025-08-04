"""
WebSocket API endpoints for real-time notifications.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Header, Query
from typing import Optional

from ..services.notification_manager import connection_manager
from ..dependencies import get_user_id_from_header

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: Optional[str] = Query(default=None, alias="user-id")
):
    """
    WebSocket endpoint for real-time notifications.
    
    Client should connect with user-id as query parameter:
    ws://localhost:8000/ws/notifications?user-id=user123
    """
    if not user_id:
        await websocket.close(code=1008, reason="Missing user-id parameter")
        return
    
    try:
        await connection_manager.connect(websocket, user_id)
        
        # Send initial connection confirmation
        await websocket.send_text('{"type": "connection_established", "data": {"user_id": "' + user_id + '"}}')
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for any message from client (could be ping/heartbeat)
                data = await websocket.receive_text()
                logger.debug(f"📡 Received message from user {user_id}: {data}")
                
                # Echo back as heartbeat response
                await websocket.send_text('{"type": "heartbeat", "data": {"status": "alive"}}')
                
            except WebSocketDisconnect:
                logger.info(f"📡 User {user_id} disconnected normally")
                break
            except Exception as e:
                logger.error(f"📡 Error handling message from user {user_id}: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"📡 User {user_id} disconnected during setup")
    except Exception as e:
        logger.error(f"📡 Error in websocket connection for user {user_id}: {e}")
    finally:
        connection_manager.disconnect(websocket, user_id)


@router.get("/notifications/status")
async def get_notification_status(user_id: str = Header(alias="user-id")):
    """Get notification system status for debugging."""
    return {
        "total_connections": connection_manager.get_connection_count(),
        "user_connections": connection_manager.get_connection_count(user_id),
        "active_users": len(connection_manager.active_connections)
    }