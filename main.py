from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

from dispatchers.connection import Connection

app = FastAPI()


manager = Connection()


@app.websocket("/apiws")
async def websocket_endpoint(websocket: WebSocket):

    await manager.connect(websocket)
    try:
        while True:
            await manager.receive_message(websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

uvicorn.run(app, host="0.0.0.0", port=8000)

# imitation of Data Base
USER_DB = {}
SESSION = {}