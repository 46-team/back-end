from bson import ObjectId

from dispatchers.tournaments.create import create_tournament_handler
from tests.test_tournament_service import FakeDb


async def test_create_tournament_handler_rejects_invalid_token(client, encryption_keys, proto):
    await create_tournament_handler(
        client=client,
        message={"device_token": "missing", "title": "Spring Cup"},
        db=FakeDb(),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "create_tournament"
    assert payload["error"] == "Authentication required"


async def test_create_tournament_handler_rejects_missing_token(client, encryption_keys, proto):
    await create_tournament_handler(
        client=client,
        message={"title": "Spring Cup"},
        db=FakeDb(),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "create_tournament"
    assert payload["error"] == "Authentication required"


async def test_create_tournament_handler_returns_created_tournament(client, encryption_keys, proto):
    token = "organizer-token"
    user_id = ObjectId()
    db = FakeDb()

    await create_tournament_handler(
        client=client,
        message={
            "device_token": token,
            "title": "Spring Cup",
            "description": "Test event",
        },
        db=db,
        USER_TOKENS={
            token: [client, {"_id": user_id, "role": "organizer"}, False, "login", {}]
        },
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "create_tournament"
    assert payload["tournament"]["title"] == "Spring Cup"
    assert payload["tournament"]["created_by"] == str(user_id)
    assert db.tournaments.insert_one_calls[0]["title"] == "Spring Cup"
