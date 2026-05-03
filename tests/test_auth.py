import asyncio
from unittest.mock import AsyncMock

from bson import ObjectId

from dispatchers.authentication.auth import server_auth


async def test_auth_finds_user_by_email_without_login_field(client, encryption_keys, proto):
    user_id = ObjectId()
    user = {
        "_id": user_id,
        "email": "alice@example.com",
        "password": "secret123",
        "role": "team",
    }
    users_collection = type("UsersCollection", (), {})()
    users_collection.find_one = AsyncMock(return_value=user)
    users_collection.update_one = AsyncMock()
    db = {"users": users_collection}
    user_tokens = {}
    save_tokens = AsyncMock()

    await server_auth(
        client=client,
        message={
            "type": "auth",
            "email": " alice@example.com ",
            "password": "secret123",
        },
        db=db,
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    users_collection.find_one.assert_awaited_once_with({"email": "alice@example.com"})
    save_tokens.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "auth"
    assert payload["auth_mode"] == "login"
    assert payload["user"] == {
        "_id": str(user_id),
        "email": "alice@example.com",
        "role": "team",
    }
    assert len(user_tokens) == 1


async def test_auth_rejects_wrong_password_without_saving_token(client, encryption_keys, proto):
    user = {
        "_id": ObjectId(),
        "email": "alice@example.com",
        "password": "secret123",
        "role": "team",
    }
    users_collection = type("UsersCollection", (), {})()
    users_collection.find_one = AsyncMock(return_value=user)
    users_collection.update_one = AsyncMock()
    db = {"users": users_collection}
    user_tokens = {}
    save_tokens = AsyncMock()

    await server_auth(
        client=client,
        message={
            "type": "auth",
            "email": "alice@example.com",
            "password": "wrong-password",
        },
        db=db,
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    await asyncio.sleep(0)
    save_tokens.assert_not_awaited()
    assert user_tokens == {}
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["err_code"] == "#INCORRECT_LOGIN"


async def test_auth_rejects_missing_email(client, encryption_keys, proto):
    users_collection = type("UsersCollection", (), {})()
    users_collection.find_one = AsyncMock()
    db = {"users": users_collection}

    await server_auth(
        client=client,
        message={
            "type": "auth",
            "password": "secret123",
        },
        db=db,
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=AsyncMock(),
    )

    await asyncio.sleep(0)
    users_collection.find_one.assert_not_awaited()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["err_code"] == "#INCORRECT_LOGIN"
