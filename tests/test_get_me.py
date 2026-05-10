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
    save_tokens = AsyncMock()

    await get_me_handler(
        client=client,
        message={"device_token": token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    proto.send_message.assert_awaited_once()
    payload, used_key = proto.send_message.await_args.args
    new_token = payload["token"]
    assert payload == {
        "is_ok": True,
        "type": "get_me",
        "token": new_token,
        "user": {"_id": str(user_id), "login": "alice"},
    }
    assert used_key == b"secret"
    assert token not in user_tokens
    assert user_tokens[new_token][0] == client
    save_tokens.assert_awaited_once()


async def test_get_me_rebinds_valid_token_from_stale_client(client, encryption_keys, proto):
    stale_client = object()
    user_id = ObjectId()
    token = "token-1"
    user_tokens = {
        token: [stale_client, {"_id": user_id, "login": "alice"}, False, "login", {}]
    }
    save_tokens = AsyncMock()

    await get_me_handler(
        client=client,
        message={"device_token": token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    proto.send_message.assert_awaited_once()
    payload, used_key = proto.send_message.await_args.args
    new_token = payload["token"]
    assert payload == {
        "is_ok": True,
        "type": "get_me",
        "token": new_token,
        "user": {"_id": str(user_id), "login": "alice"},
    }
    assert used_key == b"secret"
    assert token not in user_tokens
    assert new_token in user_tokens
    assert user_tokens[new_token][0] == client
    save_tokens.assert_awaited_once()


async def test_get_me_invalidates_old_token_after_success(client, encryption_keys, proto):
    old_token = "token-1"
    user_tokens = {
        old_token: [client, {"_id": ObjectId(), "login": "alice"}, False, "login", {}]
    }
    save_tokens = AsyncMock()

    await get_me_handler(
        client=client,
        message={"device_token": old_token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    rotated_token = proto.send_message.await_args.args[0]["token"]
    proto.send_message.reset_mock()

    await get_me_handler(
        client=client,
        message={"device_token": old_token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    await asyncio.sleep(0)
    assert old_token not in user_tokens
    assert rotated_token in user_tokens
    assert save_tokens.await_count == 1
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_me"
    assert payload["err_code"] == "#INSECURE_CONNECTION"


async def test_get_me_rejects_missing_token(client, encryption_keys, proto):
    save_tokens = AsyncMock()

    await get_me_handler(
        client=client,
        message={},
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    await asyncio.sleep(0)
    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_me"
    assert payload["error"] == "Unable to establish a secure connection. Please try again later."
    assert payload["err_code"] == "#INSECURE_CONNECTION"
    save_tokens.assert_not_awaited()


async def test_get_me_rejects_invalid_token(client, encryption_keys, proto):
    save_tokens = AsyncMock()

    await get_me_handler(
        client=client,
        message={"device_token": "missing"},
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    await asyncio.sleep(0)
    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_me"
    assert payload["error"] == "Unable to establish a secure connection. Please try again later."
    assert payload["err_code"] == "#INSECURE_CONNECTION"
    save_tokens.assert_not_awaited()


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
        save_tokens=save_tokens,
    )
    new_token = proto.send_message.await_args.args[0]["token"]

    await logout_handler(
        client=client,
        message={"device_token": new_token},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    assert token not in user_tokens
    assert new_token not in user_tokens
    assert save_tokens.await_count == 2
    assert proto.send_message.await_count == 2
    logout_payload, used_key = proto.send_message.await_args.args
    assert logout_payload == {
        "is_ok": True,
        "type": "logout",
    }
    assert used_key == b"secret"
