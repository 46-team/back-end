from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

class Connection:
    def __init__(self):
        self.active_connections = []
        self.message_queue = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def receive_message(self, websocket: WebSocket):
        data = json.loads(await websocket.receive_text())
        if type(data) != dict:
            await self.send_error(websocket, "BAD_MESSAGE_TYPE", "Unable to handle your message, because it does not contain JSON.")
            return
        if websocket not in self.message_queue.keys():
            self.message_queue[websocket] = []
        self.message_queue[websocket].append(data)

    async def send_error(self, websocket: WebSocket, error_code: str, error_message: str, need_to_disconnect = False):
        await websocket.send_json({"is_ok": False, "error_code": f"#{error_code}", "error_message": error_message})
        if need_to_disconnect:
            self.disconnect(websocket)
