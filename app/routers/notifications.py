# app/routers/notifications.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from typing import Dict, List
from app.core.dependencies import get_current_user_ws
from app.core.database import get_session
from app.models.user import User

router = APIRouter()

# in-memory store of active WS connections
active_connections: Dict[int, List[WebSocket]] = {}

@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    # Perform authentication (this will close the socket if invalid)
    user: User = await get_current_user_ws(websocket)
    if not user:
        return

    await websocket.accept()
    active_connections.setdefault(user.id, []).append(websocket)

    try:
        while True:
            # You can receive heartbeat messages if you like
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        # Ensure the connection is removed
        conns = active_connections.get(user.id, [])
        if websocket in conns:
            conns.remove(websocket)
# Utility function used in your event-change code
async def notify_user(user_id: int, payload: dict):
    """Send a JSON message to every WebSocket for this user."""
    conns = active_connections.get(user_id, [])
    for ws in conns:
        await ws.send_json(payload)