from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import db
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(
            {"event": "analytics_updated", "data": db.get_analytics()}
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
