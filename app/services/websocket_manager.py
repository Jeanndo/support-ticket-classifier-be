import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active:
                self.active.remove(websocket)

    async def broadcast(self, event: str, data: Any) -> None:
        message = json.dumps({"event": event, "data": data})
        dead: list[WebSocket] = []
        async with self._lock:
            connections = list(self.active)
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self.active:
                        self.active.remove(ws)


ws_manager = ConnectionManager()
