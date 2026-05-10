from typing import TYPE_CHECKING, Any
from fastapi import WebSocket
from dispatchers.authentication.tokens import generate_device_token
from dispatchers.utils.error_templates import (
    err_user_already_exists,
    err_incompl_request,
    err_invalid_password,
    err_invalid_email,
)
from dispatchers.utils.serializers import serialize_public_user
from dispatchers.utils.validators import is_valid_email_format
from dispatchers.authentication.roles import DEFAULT_ROLE, normalize_user_role

if TYPE_CHECKING:
    import dispatchers.utils.FGProto as FGProto
else:
    FGProto = Any


DEFAULT_REGISTERED_USER_ROLE = DEFAULT_ROLE


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

    login = message['login'].strip().lower()
    email = message.get('email', '').strip().lower()
    full_name = message.get('full_name', '').strip()

    if len(login) < 3:
        await err_incompl_request(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    if len(message['password']) < 6:
        await err_invalid_password(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    if email and not is_valid_email_format(email):
        await err_invalid_email(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    existing_user = await db['users'].find_one({
        "$or": [
            {"login": login},
            {"email": email},
        ]
    })
    if existing_user:
        await err_user_already_exists(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    message['login'] = login
    message['email'] = email
    message['full_name'] = full_name

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
        "login": message['login'],
        "email": message['email'],
        "full_name": message['full_name'],
        "password": message['password'],
        "role": DEFAULT_REGISTERED_USER_ROLE,
    }

    result = await db['users'].insert_one(user_doc)
    user_doc['_id'] = result.inserted_id
    normalize_user_role(user_doc)

    token = generate_device_token()
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
            "user":      serialize_public_user(user_doc)
        },
        ENCRYPTION_KEYS[client]['key']
    )
