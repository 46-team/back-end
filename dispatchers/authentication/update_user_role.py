from bson import ObjectId
from bson.errors import InvalidId


ALLOWED_ROLES = {"admin", "team", "jury", "organizer"}
MESSAGE_TYPE = "update_user_role"


async def send_update_role_error(client, proto, ENCRYPTION_KEYS, error):
    await proto.send_message(
        {
            "is_ok": False,
            "type": MESSAGE_TYPE,
            "error": error
        },
        ENCRYPTION_KEYS[client]['key']
    )


def serialize_user(user):
    user_data = user.copy()

    if "_id" in user_data:
        user_data["_id"] = str(user_data["_id"])

    if "password" in user_data:
        del user_data["password"]

    return user_data


async def sync_active_user_sessions(USER_TOKENS, user_id, role):
    for session in USER_TOKENS.values():
        if len(session) < 2 or not isinstance(session[1], dict):
            continue

        session_user = session[1]
        if session_user.get("_id") == user_id:
            session_user["role"] = role


async def update_user_role_handler(client, message, db, USER_TOKENS, proto, ENCRYPTION_KEYS):
    token = message.get("device_token")
    target_user_id = message.get("target_user_id") or message.get("user_id")
    requested_role = message.get("role")

    if isinstance(requested_role, str):
        requested_role = requested_role.strip().lower()

    if not token or token not in USER_TOKENS:
        await send_update_role_error(client, proto, ENCRYPTION_KEYS, "Authentication required")
        return

    requester = USER_TOKENS[token][1]

    if requester.get("role") != "admin":
        await send_update_role_error(client, proto, ENCRYPTION_KEYS, "Access denied")
        return

    if not target_user_id or not requested_role:
        await send_update_role_error(client, proto, ENCRYPTION_KEYS, "Required data is missing")
        return

    if requested_role not in ALLOWED_ROLES:
        await send_update_role_error(client, proto, ENCRYPTION_KEYS, "Invalid role")
        return

    try:
        target_object_id = ObjectId(target_user_id)
    except (InvalidId, TypeError):
        await send_update_role_error(client, proto, ENCRYPTION_KEYS, "User not found")
        return

    if requester.get("_id") == target_object_id:
        await send_update_role_error(client, proto, ENCRYPTION_KEYS, "Users cannot change their own role")
        return

    target_user = await db["users"].find_one({"_id": target_object_id})

    if not target_user:
        await send_update_role_error(client, proto, ENCRYPTION_KEYS, "User not found")
        return

    await db["users"].update_one(
        {"_id": target_object_id},
        {"$set": {"role": requested_role}}
    )

    target_user["role"] = requested_role
    await sync_active_user_sessions(USER_TOKENS, target_object_id, requested_role)

    await proto.send_message(
        {
            "is_ok": True,
            "type": MESSAGE_TYPE,
            "user": serialize_user(target_user)
        },
        ENCRYPTION_KEYS[client]['key']
    )
