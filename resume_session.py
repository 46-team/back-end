from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid

app = FastAPI()

# --- Mock database for example ---
fake_db_sessions = {
    "OLD_TOKEN_123": {"user_id": 1, "status": "disconnected", "is_valid": True}
}
fake_db_users = {
    1: {"id": 1, "username": "developer", "email": "dev@example.com"}
}

# --- Helper function for responses ---
async def send_response(websocket: WebSocket, is_ok: bool, msg_type: str, data: dict):
    """Formats and sends the response according to our standard."""
    response = {
        "is_ok": is_ok,
        "type": msg_type,
        "data": data
    }
    await websocket.send_json(response)


# --- resume-session handler ---
async def handle_resume_session(websocket: WebSocket, data: dict):
    response_type = "resume-session"
    device_token = data.get("device_token")

    # 1. Fetch the session 
    session = fake_db_sessions.get(device_token)

    # 2. Check: is the token valid
    if not session or not session.get("is_valid"):
        return await send_response(websocket, False, response_type, {
            "error": "Invalid or expired device token."
        })

    # 3. Check: was the user properly disconnected
    if session.get("status") != "disconnected":
        return await send_response(websocket, False, response_type, {
            "error": "Cannot resume session. Device was not properly disconnected."
        })

    # 4. Success: Generate a new token and fetch the user
    new_device_token = str(uuid.uuid4())
    user_id = session["user_id"]
    user_object = fake_db_users.get(user_id)

    # Update session state in DB 
    session["status"] = "connected"
    fake_db_sessions[new_device_token] = session 

    # 5. Send the successful response
    await send_response(websocket, True, response_type, {
        "device_token": new_device_token,
        "user": user_object
    })


# Add new message types and their handlers here
message_handlers = {
    "resume-session": handle_resume_session,
    # "auth": handle_auth,
}


# --- Main WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # FastAPI automatically parses the incoming string into a JSON 
            message = await websocket.receive_json()
            
            msg_type = message.get("type")
            msg_data = message.get("data", {})
            
            # Find the corresponding handler
            handler = message_handlers.get(msg_type)
            
            if handler:
                await handler(websocket, msg_data)
            else:
                await send_response(websocket, False, "error", {"message": "Unknown message type"})
                
    except WebSocketDisconnect:
        # Code reaches here if the client drops the connection 
        print("Client disconnected. Need to update DB status to 'disconnected' here.")
        
    except Exception as e:
        # Catch parsing errors  or other crashes
        await send_response(websocket, False, "error", {"message": "Invalid JSON format or server error"})
