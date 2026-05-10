import asyncio
from unittest.mock import AsyncMock

from bson import ObjectId

from dispatchers.authentication.register_account import server_register


async def test_register_rejects_short_password(client, encryption_keys, proto):
    db = {"users": type("UsersCollection", (), {"find_one": AsyncMock()})()}

    await server_register(
        client=client,
        message={
            "login": "alice",
            "password": "123",
            "full_name": "Alice Example",
            "email": "alice@example.com",
        },
        db=db,
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=AsyncMock(),
    )

    await asyncio.sleep(0)
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["error"] == "Password must contain at least 6 characters."


async def test_register_rejects_invalid_email_format(client, encryption_keys, proto):
    users_collection = type("UsersCollection", (), {"find_one": AsyncMock()})()
    db = {"users": users_collection}

    await server_register(
        client=client,
        message={
            "login": "alice",
            "password": "123456",
            "full_name": "Alice Example",
            "email": "lol",
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
    assert payload["error"] == "Invalid email format."
    assert payload["err_code"] == "#INVALID_EMAIL"


async def test_register_creates_user_with_default_role(client, encryption_keys, proto):
    users_collection = type("UsersCollection", (), {})()
    users_collection.find_one = AsyncMock(return_value=None)
    users_collection.insert_one = AsyncMock(return_value=type("InsertResult", (), {"inserted_id": ObjectId()})())
    db = {"users": users_collection}
    user_tokens = {}
    save_tokens = AsyncMock()

    await server_register(
        client=client,
        message={
            "login": "alice",
            "password": "123456",
            "full_name": "Alice Example",
            "email": "alice@example.com",
        },
        db=db,
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=save_tokens,
    )

    users_collection.insert_one.assert_awaited_once()
    inserted_user = users_collection.insert_one.await_args.args[0]
    assert inserted_user["role"] == "team"
    save_tokens.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "register_account"
    assert payload["auth_mode"] == "register"
