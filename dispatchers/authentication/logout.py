from fastapi import WebSocket
from dispatchers.utils.error_templates import err_invalid_token


async def logout_handler(client: WebSocket, message: dict, USER_TOKENS: dict, proto, ENCRYPTION_KEYS, save_tokens):
    token = message.get("device_token")

    if not token:
        await err_invalid_token(proto, ENCRYPTION_KEYS, client, type="logout")
        return

    if token not in USER_TOKENS:
        await err_invalid_token(proto, ENCRYPTION_KEYS, client, type="logout")
        return

    session = USER_TOKENS[token]

    if session[0] != client:
        await err_invalid_token(proto, ENCRYPTION_KEYS, client, type="logout")
        return

    del USER_TOKENS[token]
    await save_tokens()

    await proto.send_message(
        {
            "is_ok": True,
            "type": "logout"
        },
        ENCRYPTION_KEYS[client]['key']
    )
