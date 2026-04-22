import hashlib
import uuid
from fastapi import WebSocket
import dispatchers.utils.FGProto as FGProto
from websocket import save_tokens
from dispatchers.utils.error_templates import (
    err_unknown_mode,
    err_user_already_exists,
    err_incompl_request,
    err_invalid_password
)


DEFAULT_REGISTERED_USER_ROLE = "Team"


async def server_register(
    client: WebSocket,
    message: dict,
    db: any,
    USER_TOKENS: dict,
    proto: FGProto,
    ENCRYPTION_KEYS: dict,
    save_tokens: any
) -> None:
    
    if not message.get('login') or not message.get('password') or not message.get('full_name'):
        await err_incompl_request(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    message['login'] = message['login'].strip()

    
    if len(message['login']) < 3:
        await err_incompl_request(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    if len(message['password']) < 6:
        await err_invalid_password(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    
    existing_user = await db['users'].find_one({"login": message['login'], "email": message['email']})
    if existing_user:
        await err_user_already_exists(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    await server_register_create_user(
        client=client,
        message=message,
        db=db,
        USER_TOKENS=USER_TOKENS,
        proto=proto,
        ENCRYPTION_KEYS=ENCRYPTION_KEYS,
        save_tokens=save_tokens
    )


async def server_register_create_user(
    client: WebSocket,
    message: dict,
    db: any,
    USER_TOKENS: dict,
    proto: FGProto,
    ENCRYPTION_KEYS: dict,
    save_tokens: any
) -> None:
  
    user_doc = {
        "email":      message.get('email', '').strip(),
        "full_name":   message.get('full_name', '').strip(),
        "password":   message['password'],
        "role": DEFAULT_REGISTERED_USER_ROLE
    }

    result = await db['users'].insert_one(user_doc)
    user_doc['_id'] = result['_id']

    token = hashlib.sha256(uuid.uuid4().hex.encode('utf-8')).hexdigest()
    USER_TOKENS[token] = [
        client,
        user_doc,
        False,
        "register",
        {"is_frozen": False, "is_online": True, "last_seen": None, "login_at": None}
    ]
    await save_tokens()

    await proto.send_message(
        {
            "is_ok":     True,
            "type":      "register_account",
            "token":     token,
            "auth_mode": "register",
            "user":      user_doc
        },
        ENCRYPTION_KEYS[client]['key']
    )
