import hashlib
import uuid
from fastapi import WebSocket
import dispatchers.utils.FGProto as FGProto
from dispatchers.authentication.roles import normalize_user_role
from dispatchers.utils.error_templates import err_incorrect_login, err_unknown_mode
from dispatchers.utils.serializers import serialize_public_user


async def server_auth(client:WebSocket, message:dict, db:any, USER_TOKENS:dict, proto:FGProto, ENCRYPTION_KEYS:dict, save_tokens:any) -> None:
    message['login'] = message['login'].strip()
    user = await db['users'].find_one({"login": message['login']})
    if user:
        await server_auth_found_user(db, USER_TOKENS, client, user, proto, ENCRYPTION_KEYS, save_tokens, message)
    else:
        await err_incorrect_login(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)


async def server_auth_found_user(db:any, USER_TOKENS:dict, client:WebSocket, user:dict, proto:FGProto, ENCRYPTION_KEYS:dict, save_tokens:any, message:dict) -> None:
    stored_role = user.get("role")
    normalized_role = normalize_user_role(user)
    if normalized_role and stored_role != normalized_role:
        await db['users'].update_one({"_id": user["_id"]}, {"$set": {"role": normalized_role}})
    token = hashlib.sha256(uuid.uuid4().hex.encode('utf-8')).hexdigest()
    USER_TOKENS[token] = [client, user, False, "login", {"is_frozen": False, "is_online": True, "last_seen": None, "login_at": None}]
    await save_tokens()
    userr = serialize_public_user(user)
    if message['login'].strip() == user['login'].strip():
        if message['password'] == user['password']:
            await proto.send_message({"is_ok": True, "type": "auth", "token": token, "auth_mode": "login", "user": userr}, ENCRYPTION_KEYS[client]['key'])
        else:
            await err_incorrect_login(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client)
    else:
        await err_unknown_mode(proto=proto, ENCRYPTION_KEYS=ENCRYPTION_KEYS, client=client, type=message['type'])

