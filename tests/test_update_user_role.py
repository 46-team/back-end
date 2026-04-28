from bson import ObjectId

from dispatchers.authentication.update_user_role import update_user_role_handler


async def test_update_user_role_requires_admin(client, encryption_keys, proto):
    token = "admin-token"
    user_tokens = {
        token: [client, {"_id": ObjectId(), "role": "team"}, False, "login", {}]
    }

    await update_user_role_handler(
        client=client,
        message={
            "device_token": token,
            "target_user_id": str(ObjectId()),
            "role": "jury",
        },
        db={},
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["error"] == "Access denied"


async def test_update_user_role_updates_db_and_active_session(client, encryption_keys, proto):
    admin_id = ObjectId()
    target_id = ObjectId()
    token = "admin-token"
    second_token = "target-token"
    users_collection = type("UsersCollection", (), {})()
    users_collection.find_one = __import__("unittest.mock").mock.AsyncMock(
        return_value={"_id": target_id, "login": "bob", "password": "secret", "role": "team"}
    )
    users_collection.update_one = __import__("unittest.mock").mock.AsyncMock()
    db = {"users": users_collection}
    user_tokens = {
        token: [client, {"_id": admin_id, "role": "admin"}, False, "login", {}],
        second_token: [object(), {"_id": target_id, "role": "team"}, False, "login", {}],
    }

    await update_user_role_handler(
        client=client,
        message={
            "device_token": token,
            "target_user_id": str(target_id),
            "role": "jury",
        },
        db=db,
        USER_TOKENS=user_tokens,
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    users_collection.update_one.assert_awaited_once()
    assert user_tokens[second_token][1]["role"] == "jury"
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["user"]["_id"] == str(target_id)
    assert payload["user"]["role"] == "jury"
    assert "password" not in payload["user"]
