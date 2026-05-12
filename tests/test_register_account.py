import asyncio
from unittest.mock import AsyncMock

import pytest
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


async def test_register_rejects_login_longer_than_30_characters(client, encryption_keys, proto):
    users_collection = type("UsersCollection", (), {"find_one": AsyncMock()})()
    db = {"users": users_collection}

    await server_register(
        client=client,
        message={
            "login": "a" * 31,
            "password": "123456",
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
    users_collection.find_one.assert_not_awaited()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["err_code"] == "#INVALID_LOGIN"
    assert payload["error"] == (
        "Login must be 3-30 characters and may contain only Latin letters, digits, '.', "
        "'_', and '-'. It must start and end with a letter or digit."
    )


@pytest.mark.parametrize("login", ["player+1", "player 1", ".player", "player_", "гравець", "player/name"])
async def test_register_rejects_invalid_login_format(client, encryption_keys, proto, login):
    users_collection = type("UsersCollection", (), {"find_one": AsyncMock()})()
    db = {"users": users_collection}

    await server_register(
        client=client,
        message={
            "login": login,
            "password": "123456",
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
    users_collection.find_one.assert_not_awaited()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["err_code"] == "#INVALID_LOGIN"
    assert payload["error"] == (
        "Login must be 3-30 characters and may contain only Latin letters, digits, '.', "
        "'_', and '-'. It must start and end with a letter or digit."
    )


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


async def test_register_allows_common_login_separators(client, encryption_keys, proto):
    users_collection = type("UsersCollection", (), {})()
    users_collection.find_one = AsyncMock(return_value=None)
    users_collection.insert_one = AsyncMock(return_value=type("InsertResult", (), {"inserted_id": ObjectId()})())
    db = {"users": users_collection}

    await server_register(
        client=client,
        message={
            "login": " Player_1.2-test ",
            "password": "123456",
            "full_name": "Alice Example",
            "email": "alice@example.com",
        },
        db=db,
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=AsyncMock(),
    )

    users_collection.find_one.assert_awaited_once_with({
        "$or": [
            {"login": "player_1.2-test"},
            {"email": "alice@example.com"},
        ]
    })
    inserted_user = users_collection.insert_one.await_args.args[0]
    assert inserted_user["login"] == "player_1.2-test"


async def test_register_normalizes_email_to_lowercase(client, encryption_keys, proto):
    users_collection = type("UsersCollection", (), {})()
    users_collection.find_one = AsyncMock(return_value=None)
    users_collection.insert_one = AsyncMock(return_value=type("InsertResult", (), {"inserted_id": ObjectId()})())
    db = {"users": users_collection}

    await server_register(
        client=client,
        message={
            "login": "alice",
            "password": "123456",
            "full_name": "Alice Example",
            "email": " Alice@Example.COM ",
        },
        db=db,
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=AsyncMock(),
    )

    users_collection.find_one.assert_awaited_once_with({
        "$or": [
            {"login": "alice"},
            {"email": "alice@example.com"},
        ]
    })
    inserted_user = users_collection.insert_one.await_args.args[0]
    assert inserted_user["email"] == "alice@example.com"


async def test_register_normalizes_login_to_lowercase(client, encryption_keys, proto):
    users_collection = type("UsersCollection", (), {})()
    users_collection.find_one = AsyncMock(return_value=None)
    users_collection.insert_one = AsyncMock(return_value=type("InsertResult", (), {"inserted_id": ObjectId()})())
    db = {"users": users_collection}

    await server_register(
        client=client,
        message={
            "login": " Alice ",
            "password": "123456",
            "full_name": "Alice Example",
            "email": "alice@example.com",
        },
        db=db,
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
        save_tokens=AsyncMock(),
    )

    users_collection.find_one.assert_awaited_once_with({
        "$or": [
            {"login": "alice"},
            {"email": "alice@example.com"},
        ]
    })
    inserted_user = users_collection.insert_one.await_args.args[0]
    assert inserted_user["login"] == "alice"
