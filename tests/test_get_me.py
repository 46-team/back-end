from bson import ObjectId

from dispatchers.authentication.get_me import get_me_handler


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


async def test_get_me_rejects_invalid_token(client, encryption_keys, proto):
    await get_me_handler(
        client=client,
        message={"device_token": "missing"},
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_me"
    assert payload["error"] == "Unable to establish a secure connection. Please try again later."
    assert payload["err_code"] == "#INSECURE_CONNECTION"
