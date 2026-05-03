import asyncio

from bson import ObjectId

from dispatchers.tournaments.tournament_get import get_tournament
from tests.test_tournament_service import FakeDb, FakeTournamentCollection


async def test_get_tournament_handler_returns_tournament(client, encryption_keys, proto):
    token = "organizer-token"
    tournament_id = ObjectId()
    organizer_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "description": "Test event",
                    "created_by": organizer_id,
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [ObjectId()],
                }
            }
        )
    )

    await get_tournament(
        client=client,
        message={
            "device_token": token,
            "tournament_id": str(tournament_id),
        },
        db=db,
        USER_TOKENS={
            token: [client, {"_id": organizer_id, "role": "organizer"}, False, "login", {}]
        },
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, used_key = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "get_tournament"
    assert payload["tournament"]["_id"] == str(tournament_id)
    assert payload["tournament"]["created_by"] == str(organizer_id)
    assert "participant_ids" not in payload["tournament"]
    assert used_key == b"secret"


async def test_get_tournament_handler_rejects_missing_token(client, encryption_keys, proto):
    await get_tournament(
        client=client,
        message={"tournament_id": str(ObjectId())},
        db=FakeDb(),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    await asyncio.sleep(0)
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["error"] == "Authorization token is missing. Please try again later."
    assert payload["err_code"] == "#AUTH_TOKEN_EMPTY"


async def test_get_tournament_handler_rejects_invalid_token(client, encryption_keys, proto):
    await get_tournament(
        client=client,
        message={
            "device_token": "missing",
            "tournament_id": str(ObjectId()),
        },
        db=FakeDb(),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    await asyncio.sleep(0)
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_tournament"
    assert payload["err_code"] == "#INSECURE_CONNECTION"


async def test_get_tournament_handler_rejects_invalid_id(client, encryption_keys, proto):
    token = "organizer-token"

    await get_tournament(
        client=client,
        message={
            "device_token": token,
            "tournament_id": "not-an-object-id",
        },
        db=FakeDb(),
        USER_TOKENS={
            token: [client, {"_id": ObjectId(), "role": "organizer"}, False, "login", {}]
        },
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    await asyncio.sleep(0)
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_tournament"
    assert payload["err_code"] == "#INVALID_ID"


async def test_get_tournament_handler_returns_not_found(client, encryption_keys, proto):
    token = "organizer-token"

    await get_tournament(
        client=client,
        message={
            "device_token": token,
            "tournament_id": str(ObjectId()),
        },
        db=FakeDb(),
        USER_TOKENS={
            token: [client, {"_id": ObjectId(), "role": "organizer"}, False, "login", {}]
        },
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    await asyncio.sleep(0)
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_tournament"
    assert payload["err_code"] == "#NOT_FOUND"
