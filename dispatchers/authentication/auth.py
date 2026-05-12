from typing import TYPE_CHECKING, Any
from fastapi import WebSocket
from dispatchers.authentication.roles import normalize_user_role
from dispatchers.authentication.tokens import generate_device_token
from dispatchers.utils.error_templates import err_incorrect_login
from dispatchers.utils.serializers import serialize_public_user

if TYPE_CHECKING:
    import dispatchers.utils.FGProto as FGProto
else:
    FGProto = Any


async def server_auth(client:WebSocket, message:dict, db:any, USER_TOKENS:dict, proto:FGProto, ENCRYPTION_KEYS:dict, save_tokens:any) -> None:
    email = message.get('email', '').strip().lower()
    login = (message.get('login') or message.get('username') or '').strip().lower()
    if not email and not login:
        await err_incorrect_login(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    message['email'] = email
    message['login'] = login
    if email and login:
        user = await db['users'].find_one({"$or": [{"email": email}, {"login": login}]})
    elif email:
        user = await db['users'].find_one({"email": email})
        if not user:
            user = await db['users'].find_one({"login": email})
    else:
        user = await db['users'].find_one({"login": login})

    if user:
        await server_auth_found_user(db, USER_TOKENS, client, user, proto, ENCRYPTION_KEYS, save_tokens, message)
    else:
        await err_incorrect_login(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)


async def server_auth_found_user(db:any, USER_TOKENS:dict, client:WebSocket, user:dict, proto:FGProto, ENCRYPTION_KEYS:dict, save_tokens:any, message:dict) -> None:
    if message['password'] != user['password']:
        await err_incorrect_login(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
        return

    stored_role = user.get("role")
    normalized_role = normalize_user_role(user)
    if normalized_role and stored_role != normalized_role:
        await db['users'].update_one({"_id": user["_id"]}, {"$set": {"role": normalized_role}})
    token = generate_device_token()
    USER_TOKENS[token] = [client, user, False, "login", {"is_frozen": False, "is_online": True, "last_seen": None, "login_at": None}]
    await save_tokens()
    userr = serialize_public_user(user)
    await proto.send_message({"is_ok": True, "type": "auth", "token": token, "auth_mode": "login", "user": userr}, ENCRYPTION_KEYS[client]['key'])

