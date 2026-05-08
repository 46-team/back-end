from bson import ObjectId

from dispatchers.tournaments.update import update_tournament_handler
from tests.test_tournament_service import FakeDb, FakeTournamentCollection


async def test_update_tournament_handler_requires_authentication(client, encryption_keys, proto):
    await update_tournament_handler(
        client=client,
        message={"device_token": "missing", "tournament_id": str(ObjectId())},
        db=FakeDb(),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "update_tournament"
    assert payload["error"] == "Authentication required"


async def test_update_tournament_handler_returns_updated_tournament(client, encryption_keys, proto):
    token = "organizer-token"
    tournament_id = ObjectId()
    organizer_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "description": "Old description",
                    "created_by": organizer_id,
                    "start_date": "2026-05-10",
                    "end_date": "2026-05-12",
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [],
                }
            }
        )
    )

    await update_tournament_handler(
        client=client,
        message={
            "device_token": token,
            "tournament_id": str(tournament_id),
            "title": "Summer Cup",
            "description": "New description",
            "start_date": "2026-05-11",
            "end_date": "2026-05-13",
        },
        db=db,
        USER_TOKENS={
            token: [client, {"_id": organizer_id, "role": "organizer"}, False, "login", {}]
        },
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "update_tournament"
    assert payload["tournament"]["_id"] == str(tournament_id)
    assert payload["tournament"]["title"] == "Summer Cup"
    assert payload["tournament"]["description"] == "New description"
    assert payload["tournament"]["start_date"] == "2026-05-11"
    assert payload["tournament"]["end_date"] == "2026-05-13"
    assert isinstance(payload["tournament"]["updated_at"], int)
