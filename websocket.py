import base64
import json
import logging
import os
import time
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI
from starlette.websockets import WebSocket, WebSocketDisconnect

from dispatchers.authentication import auth
from dispatchers.utils.error_templates import err_unknown_request
from dispatchers.utils.utils import find_token_by_websocket
from dispatchers.utils import FGProto as fgproto
app = FastAPI()
active_connections = set()
ENCRYPTION_KEYS = {}
logger = logging.getLogger(__name__)
USER_TOKENS = {}
USER_TOKEN_EXPIRY_VARIANTS = [60 * 60 * 24 * 7, 60 * 60 * 24 * 30, 60 * 60 * 24 * 30 * 3, 60 * 60 * 24 * 30 * 6,
                              60 * 60 * 24 * 30 * 12]
FREEZE_SESSIONS = {}

async def message_handler(websocket: WebSocket, message: str):
    global USER_TOKENS, FREEZE_SESSIONS
    from main import db
    message = json.loads(message)
    proto = fgproto.FGProto(type="ws", client=websocket)
    if message['type'] == 'auth':
        await auth.server_auth(client=websocket, message=message, db=db, USER_TOKENS=USER_TOKENS, proto=proto,
                          ENCRYPTION_KEYS=ENCRYPTION_KEYS, save_tokens=save_tokens)
    elif message['type'] == "echo":
        await proto.send_message({"is_ok": True, "type": "echo", "message": message['message']},
                                 ENCRYPTION_KEYS[websocket]['key'])
    elif message['type'] == "get_me":
        from dispatchers.authentication.get_me import get_me_handler
        await get_me_handler(
            client=websocket,
            message=message,
            USER_TOKENS=USER_TOKENS,
            proto=proto,
            ENCRYPTION_KEYS=ENCRYPTION_KEYS
        )
    else:
        await err_unknown_request(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=websocket)




@app.websocket("/apiws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    proto = fgproto.FGProto(type="ws", client=websocket)

    try:
        while True:
            data = await websocket.receive_json()
            data['client_public_key'] = data['client_public_key'].encode('utf-8')

            if data['type'] == 'handshake_request':
                logging.info("Accepted handshake request")
                ENCRYPTION_KEYS[websocket] = {
                    'ECDH': {
                        'client_public_key': serialization.load_pem_public_key(data['client_public_key'])
                    }
                }
                handshake_res = await proto.handshake()
                if handshake_res['is_ok']:
                    print("Handshake OK")
                    ENCRYPTION_KEYS[websocket]["key"] = handshake_res['key']
                    while True:
                        enc = await websocket.receive_bytes()
                        msg = (await proto.decrypt(enc, ENCRYPTION_KEYS[websocket]["key"])).decode('utf-8')
                        await message_handler(websocket, msg)

                else:
                    print("Handshake Failed")
                    await websocket.send_bytes(
                        json.dumps({'is_ok': False, 'error': 'Handshake Failed'}).encode('utf-8'))
            else:
                await websocket.send_bytes(json.dumps({
                    'is_ok': False,
                    'error': 'It seems like you are not authorized. Make handshake request first.'
                }).encode('utf-8'))
    except WebSocketDisconnect:
        active_connections.remove(websocket)

    except json.decoder.JSONDecodeError:
        active_connections.remove(websocket)
        await websocket.send_bytes(json.dumps({
            'is_ok': False,
            'error': 'Invalid data type',
        }).encode('utf-8'))
        logging.error("Invalid data type. Closing connection...")

    finally:
        token = await find_token_by_websocket(USER_TOKENS, websocket)
        if token and token in USER_TOKENS:
            from main import db

            try:
                if len(USER_TOKENS[token]) >= 5:
                    session_data = USER_TOKENS[token][4]
                    if isinstance(session_data, dict):
                        session_data['is_frozen'] = True
                        session_data['is_online'] = False
                        session_data['last_seen'] = int(time.time())
            except Exception as e:
                print(f"[WARN] Failed to update session state: {e}")

        try:
            await websocket.close(code=1000)
        except RuntimeError as e:
            if "Unexpected ASGI message" in str(e):
                pass
            else:
                raise

async def load_tokens():
    global USER_TOKENS
    import aiofiles, os
    from bson import ObjectId

    if "SESSIONS.dat" in os.listdir("config"):
        async with aiofiles.open("config/SESSIONS.dat", "r", encoding='utf-8') as f:
            try:
                USER_TOKENS = eval(await f.read())
            except:
                USER_TOKENS = {}
        for i in USER_TOKENS.keys():
            USER_TOKENS[i][1]['_id'] = ObjectId(USER_TOKENS[i][1]['_id'])
        return USER_TOKENS
    return {}


async def save_tokens():
    import aiofiles

    data = {}

    for token, value in USER_TOKENS.items():
        new_value = list(value)

        if isinstance(new_value[1], dict) and "_id" in new_value[1]:
            new_value[1] = dict(new_value[1])
            new_value[1]["_id"] = str(new_value[1]["_id"])

        new_value[0] = None

        data[token] = new_value

    async with aiofiles.open("config/SESSIONS.dat", "w", encoding="utf-8") as f:
        await f.write(str(data))
