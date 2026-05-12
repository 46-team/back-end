import asyncio
from unittest.mock import AsyncMock

from dispatchers.authentication.logout import logout_handler


async def test_logout_removes_current_client_token_and_persists(client, encryption_keys, proto):
    token = "token-1"
    user_tokens = {
        token: [client, {"login": "alice"}, False, "login", {}]
    }
    save_tokens = AsyncMock()

    await logout_handler(
        client=client,
        message={"device_token": token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    assert token not in user_tokens
    save_tokens.assert_awaited_once()
    proto.send_message.assert_awaited_once()
    payload, used_key = proto.send_message.await_args.args
    assert payload == {
        "is_ok": True,
        "type": "logout",
    }
    assert used_key == b"secret"


async def test_logout_rejects_missing_token(client, encryption_keys, proto):
    user_tokens = {
        "token-1": [client, {"login": "alice"}, False, "login", {}]
    }
    save_tokens = AsyncMock()

    await logout_handler(
        client=client,
        message={},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    await asyncio.sleep(0)
    assert "token-1" in user_tokens
    save_tokens.assert_not_awaited()
    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "logout"
    assert payload["error"] == "Unable to establish a secure connection. Please try again later."
    assert payload["err_code"] == "#INSECURE_CONNECTION"


async def test_logout_rejects_invalid_token(client, encryption_keys, proto):
    save_tokens = AsyncMock()

    await logout_handler(
        client=client,
        message={"device_token": "missing"},
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    await asyncio.sleep(0)
    save_tokens.assert_not_awaited()
    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "logout"
    assert payload["error"] == "Unable to establish a secure connection. Please try again later."
    assert payload["err_code"] == "#INSECURE_CONNECTION"


async def test_logout_rejects_token_for_another_client(client, encryption_keys, proto):
    other_client = object()
    token = "token-1"
    user_tokens = {
        token: [other_client, {"login": "alice"}, False, "login", {}]
    }
    save_tokens = AsyncMock()

    await logout_handler(
        client=client,
        message={"device_token": token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    await asyncio.sleep(0)
    assert token in user_tokens
    save_tokens.assert_not_awaited()
    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "logout"
    assert payload["error"] == "Unable to establish a secure connection. Please try again later."
    assert payload["err_code"] == "#INSECURE_CONNECTION"
