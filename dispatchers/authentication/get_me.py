from fastapi import WebSocket
from dispatchers.utils.error_templates import err_invalid_token
from dispatchers.utils.serializers import serialize_public_user


async def get_me_handler(client: WebSocket, message: dict, USER_TOKENS: dict, proto, ENCRYPTION_KEYS):
    token = message.get("device_token")

    if not token:
        await err_invalid_token(proto, ENCRYPTION_KEYS, client, type="get_me")
        return

    if token not in USER_TOKENS:
        await err_invalid_token(proto, ENCRYPTION_KEYS, client, type="get_me")
        return

    session = USER_TOKENS[token]
    session[0] = client

    user = serialize_public_user(session[1])

    await proto.send_message(
        {
            "is_ok": True,
            "type": "get_me",
            "user": user
        },
        ENCRYPTION_KEYS[client]['key']
    )
