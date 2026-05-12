from fastapi import WebSocket
from dispatchers.authentication.tokens import generate_device_token
from dispatchers.utils.error_templates import err_invalid_token
from dispatchers.utils.serializers import serialize_public_user


async def get_me_handler(client: WebSocket, message: dict, USER_TOKENS: dict, proto, ENCRYPTION_KEYS, save_tokens):
    token = message.get("device_token")

    if not token:
        await err_invalid_token(proto, ENCRYPTION_KEYS, client, type="get_me")
        return

    if token not in USER_TOKENS:
        await err_invalid_token(proto, ENCRYPTION_KEYS, client, type="get_me")
        return

    session = USER_TOKENS.pop(token)
    session[0] = client
    new_token = generate_device_token()
    USER_TOKENS[new_token] = session
    await save_tokens()

    user = serialize_public_user(session[1])

    await proto.send_message(
        {
            "is_ok": True,
            "type": "get_me",
            "token": new_token,
            "user": user
        },
        ENCRYPTION_KEYS[client]['key']
    )
