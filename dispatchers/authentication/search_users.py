import re

from dispatchers.authentication.roles import has_role, normalize_user_role
from dispatchers.utils.serializers import PUBLIC_USER_FIELDS, serialize_public_user


MESSAGE_TYPE = "search_users"
USER_PUBLIC_PROJECTION = {field: 1 for field in PUBLIC_USER_FIELDS}
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
ELIGIBLE_PARTICIPANT_ROLES = ("team", "jury")


async def send_search_users_error(client, proto, ENCRYPTION_KEYS, error):
    await proto.send_message(
        {
            "is_ok": False,
            "type": MESSAGE_TYPE,
            "error": error
        },
        ENCRYPTION_KEYS[client]['key']
    )


def parse_limit(value):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT

    if limit < 1:
        return DEFAULT_LIMIT

    return min(limit, MAX_LIMIT)


def build_search_query(search_text):
    if not search_text or not str(search_text).strip():
        return {}

    pattern = re.escape(str(search_text).strip())
    return {
        "$or": [
            {"email": {"$regex": pattern, "$options": "i"}},
            {"full_name": {"$regex": pattern, "$options": "i"}},
            {"login": {"$regex": pattern, "$options": "i"}},
        ]
    }


def build_authorized_query(requester, purpose, search_text):
    base_query = build_search_query(search_text)

    if has_role(requester, "admin"):
        if purpose not in (None, "role_management"):
            raise Exception("Access denied")
        return base_query

    if has_role(requester, "organizer"):
        if purpose != "tournament_participants":
            raise Exception("Access denied")

        role_query = {"role": {"$in": ELIGIBLE_PARTICIPANT_ROLES}}
        if not base_query:
            return role_query

        return {"$and": [role_query, base_query]}

    raise Exception("Access denied")


async def search_users_handler(client, message, db, USER_TOKENS, proto, ENCRYPTION_KEYS):
    token = message.get("device_token")

    if not token or token not in USER_TOKENS:
        await send_search_users_error(client, proto, ENCRYPTION_KEYS, "Authentication required")
        return

    requester = USER_TOKENS[token][1]
    normalize_user_role(requester)

    try:
        query = build_authorized_query(
            requester=requester,
            purpose=message.get("purpose"),
            search_text=message.get("query") or message.get("search"),
        )
    except Exception as e:
        await send_search_users_error(client, proto, ENCRYPTION_KEYS, str(e))
        return

    cursor = db["users"].find(query, USER_PUBLIC_PROJECTION)
    if hasattr(cursor, "limit"):
        cursor = cursor.limit(parse_limit(message.get("limit")))

    users = []
    async for user in cursor:
        users.append(serialize_public_user(user))

    await proto.send_message(
        {
            "is_ok": True,
            "type": MESSAGE_TYPE,
            "users": users
        },
        ENCRYPTION_KEYS[client]['key']
    )
