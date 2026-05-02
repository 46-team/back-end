from bson import ObjectId

from dispatchers.tournaments.assign_participants import assign_tournament_participants_handler
from tests.test_tournament_service import FakeDb, FakeTournamentCollection, FakeUsersCollection


async def test_assign_tournament_participants_handler_requires_authentication(client, encryption_keys, proto):
    await assign_tournament_participants_handler(
        client=client,
        message={"device_token": "missing"},
        db=FakeDb(),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "assign_tournament_participants"
    assert payload["error"] == "Authentication required"


async def test_assign_tournament_participants_handler_returns_updated_tournament(client, encryption_keys, proto):
    token = "organizer-token"
    tournament_id = ObjectId()
    participant_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": ObjectId(),
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [],
                }
            }
        ),
        users=FakeUsersCollection(
            {
                participant_id: {"_id": participant_id, "role": "team"},
            }
        )
    )

    await assign_tournament_participants_handler(
        client=client,
        message={
            "device_token": token,
            "tournament_id": str(tournament_id),
            "participant_ids": [str(participant_id)],
        },
        db=db,
        USER_TOKENS={
            token: [client, {"_id": ObjectId(), "role": "organizer"}, False, "login", {}]
        },
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "assign_tournament_participants"
    assert payload["tournament"]["_id"] == str(tournament_id)
    assert payload["tournament"]["participant_ids"] == [str(participant_id)]
