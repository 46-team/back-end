import hashlib
import uuid
from fastapi import WebSocket
import dispatchers.utils.FGProto as FGProto
from dispatchers.utils.error_templates import (
    err_unknown_mode,
    err_user_already_exists,
    err_incompl_request,
    err_invalid_password
)


async def server_register(
    client: WebSocket,
    message: dict,
    db: any,
    USER_TOKENS: dict,
    proto: FGProto,
    ENCRYPTION_KEYS: dict,
    save_tokens: any
) -> None:
    
    if not message.get('login') or not message.get('password') or not message.get('first_name'):
        await err_incompl_request(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    message['login'] = message['login'].strip()

    
    if len(message['login']) < 3:
        await err_incompl_request(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    if len(message['password']) < 6:
        await err_invalid_password(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    
    existing_user = await db['users'].find_one({"login": message['login']})
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
    }

    result = await db['users'].insert_one(user_doc)


    token = hashlib.sha256(uuid.uuid4().hex.encode('utf-8')).hexdigest()
    USER_TOKENS[token] = [
        client,
        user_doc,
        False,
        "register",
        {"is_frozen": False, "is_online": True, "last_seen": None, "login_at": None}
    ]
    await save_tokens()

   
    userr = user_doc.copy()
    userr['id'] = str(result.inserted_id)

    await proto.send_message(
        {
            "is_ok":     True,
            "type":      "auth",
            "token":     token,
            "auth_mode": "register",
            "user":      userr
        },
        ENCRYPTION_KEYS[client]['key']
    )