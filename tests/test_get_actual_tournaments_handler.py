from bson import ObjectId

from dispatchers.tournaments.get_actual import get_actual_tournaments_handler
from tests.test_tournament_service import FakeDb, FakeTournamentCollection


async def test_get_actual_tournaments_handler_returns_available_tournaments(
    client,
    encryption_keys,
    proto,
):
    token = "team-token"
    participant_id = ObjectId()
    tournament_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": ObjectId(),
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [participant_id],
                }
            }
        )
    )

    await get_actual_tournaments_handler(
        client=client,
        message={"device_token": token},
        db=db,
        USER_TOKENS={
            token: [client, {"_id": participant_id, "role": "team"}, False, "login", {}]
        },
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "get_actual_tournaments"
    assert payload["tournaments"][0]["_id"] == str(tournament_id)


async def test_get_actual_tournaments_handler_rejects_invalid_token(
    client,
    encryption_keys,
    proto,
):
    await get_actual_tournaments_handler(
        client=client,
        message={"device_token": "missing"},
        db=FakeDb(),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    proto.send_message.assert_awaited_once()
    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "get_actual_tournaments"
    assert payload["error"] == "Invalid token"
