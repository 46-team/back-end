from bson import ObjectId

from dispatchers.tournaments.upsert_submission import upsert_tournament_submission_handler
from tests.test_tournament_service import FakeDb, FakeTournamentCollection, FakeUsersCollection


async def test_upsert_tournament_submission_handler_requires_authentication(client, encryption_keys, proto):
    await upsert_tournament_submission_handler(
        client=client,
        message={"device_token": "missing"},
        db=FakeDb(),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "upsert_tournament_submission"
    assert payload["error"] == "Authentication required"


async def test_upsert_tournament_submission_handler_returns_submission(client, encryption_keys, proto, monkeypatch):
    token = "team-token"
    tournament_id = ObjectId()
    organizer_id = ObjectId()
    team_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": organizer_id,
                    "participant_ids": [team_id],
                }
            }
        ),
        users=FakeUsersCollection({organizer_id: {"_id": organizer_id, "email": "organizer@example.com"}}),
    )

    async def fake_email_sender(**kwargs):
        return None

    monkeypatch.setattr(
        "services.email_service.send_tournament_submission_notification",
        fake_email_sender,
    )

    await upsert_tournament_submission_handler(
        client=client,
        message={
            "device_token": token,
            "tournament_id": str(tournament_id),
            "repository_url": "https://github.com/team/project",
            "video_demo_url": "https://video.example/demo",
        },
        db=db,
        USER_TOKENS={
            token: [
                client,
                {"_id": team_id, "role": "team", "email": "team@example.com"},
                False,
                "login",
                {},
            ]
        },
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "upsert_tournament_submission"
    assert payload["email_sent"] is True
    assert payload["submission"]["tournament_id"] == str(tournament_id)
    assert payload["submission"]["team_id"] == str(team_id)
