import asyncio
from unittest.mock import AsyncMock

from bson import ObjectId

from dispatchers.authentication.get_me import get_me_handler
from dispatchers.authentication.logout import logout_handler


async def test_get_me_returns_user_for_valid_session(client, encryption_keys, proto):
    user_id = ObjectId()
    token = "token-1"
    user_tokens = {
        token: [client, {"_id": user_id, "login": "alice"}, False, "login", {}]
    }

    await get_me_handler(
        client=client,
        message={"device_token": token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    proto.send_message.assert_awaited_once()
    payload, used_key = proto.send_message.await_args.args
    assert payload == {
        "is_ok": True,
        "type": "get_me",
        "user": {"_id": str(user_id), "login": "alice"},
    }
    assert used_key == b"secret"


async def test_get_me_rebinds_valid_token_from_stale_client(client, encryption_keys, proto):
    stale_client = object()
    user_id = ObjectId()
    token = "token-1"
    user_tokens = {
        token: [stale_client, {"_id": user_id, "login": "alice"}, False, "login", {}]
    }

    await get_me_handler(
        client=client,
        message={"device_token": token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    assert user_tokens[token][0] == client
    proto.send_message.assert_awaited_once()
    payload, used_key = proto.send_message.await_args.args
    assert payload == {
        "is_ok": True,
        "type": "get_me",
        "user": {"_id": str(user_id), "login": "alice"},
    }
    assert used_key == b"secret"


async def test_get_me_rejects_missing_token(client, encryption_keys, proto):
    await get_me_handler(
        client=client,
        message={},
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    await asyncio.sleep(0)
    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_me"
    assert payload["error"] == "Unable to establish a secure connection. Please try again later."
    assert payload["err_code"] == "#INSECURE_CONNECTION"


async def test_get_me_rejects_invalid_token(client, encryption_keys, proto):
    await get_me_handler(
        client=client,
        message={"device_token": "missing"},
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    await asyncio.sleep(0)
    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_me"
    assert payload["error"] == "Unable to establish a secure connection. Please try again later."
    assert payload["err_code"] == "#INSECURE_CONNECTION"


async def test_logout_can_revoke_token_after_get_me_rebinds(client, encryption_keys, proto):
    stale_client = object()
    token = "token-1"
    user_tokens = {
        token: [stale_client, {"login": "alice"}, False, "login", {}]
    }
    save_tokens = AsyncMock()

    await get_me_handler(
        client=client,
        message={"device_token": token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

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
    assert proto.send_message.await_count == 2
    logout_payload, used_key = proto.send_message.await_args.args
    assert logout_payload == {
        "is_ok": True,
        "type": "logout",
    }
    assert used_key == b"secret"
