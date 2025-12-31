from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_code: str):
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = []
        self.active_connections[room_code].append(websocket)

    def disconnect(self, websocket: WebSocket, room_code: str):
        if room_code in self.active_connections:
            if websocket in self.active_connections[room_code]:
                self.active_connections[room_code].remove(websocket)
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]

    async def broadcast(self, room_code: str, message: dict):
        if room_code in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[room_code]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    dead_connections.append(connection)
            for conn in dead_connections:
                self.disconnect(conn, room_code)


manager = ConnectionManager()


@router.websocket("/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    room_code = room_code.upper()
    await manager.connect(websocket, room_code)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "update":
                await manager.broadcast(room_code, {
                    "type": "state_update",
                    "data": message.get("data", {})
                })
            elif message.get("type") == "player_joined":
                await manager.broadcast(room_code, {
                    "type": "player_joined",
                    "nickname": message.get("nickname")
                })
            elif message.get("type") == "game_started":
                await manager.broadcast(room_code, {
                    "type": "game_started"
                })
            elif message.get("type") == "choice_made":
                await manager.broadcast(room_code, {
                    "type": "choice_made",
                    "player": message.get("player"),
                    "choice": message.get("choice")
                })
            elif message.get("type") == "turn_complete":
                await manager.broadcast(room_code, {
                    "type": "turn_complete"
                })
            elif message.get("type") == "game_finished":
                await manager.broadcast(room_code, {
                    "type": "game_finished"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)
        await manager.broadcast(room_code, {
            "type": "player_disconnected"
        })
