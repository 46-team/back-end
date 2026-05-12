from bson import ObjectId

from dispatchers.tournaments.change_tournament_status import change_tournament_status
from tests.test_tournament_service import FakeDb, FakeTournamentCollection, FakeUsersCollection


def user_token(client, token, user_id, role="organizer"):
    return {
        token: [client, {"_id": user_id, "role": role}, False, "login", {}]
    }


def db_user(user_id, role="organizer"):
    return FakeUsersCollection({user_id: {"_id": user_id, "role": role}})


async def call_handler(client, encryption_keys, proto, message, db=None, tokens=None):
    await change_tournament_status(
        client=client,
        message=message,
        db=db or FakeDb(),
        USER_TOKENS=tokens or {},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    return proto.send_message.await_args.args[0]


async def test_change_tournament_status_returns_updated_tournament(client, encryption_keys, proto):
    token = "organizer-token"
    tournament_id = ObjectId()
    organizer_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": organizer_id,
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [],
                }
            }
        ),
        users=db_user(organizer_id),
    )

    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {
            "device_token": token,
            "tournament_id": str(tournament_id),
            "status": "Registration",
        },
        db=db,
        tokens=user_token(client, token, organizer_id),
    )

    assert payload["is_ok"] is True
    assert payload["type"] == "change_tournament_status"
    assert payload["tournament"]["_id"] == str(tournament_id)
    assert payload["tournament"]["status"] == "Registration"
    assert isinstance(payload["tournament"]["updated_at"], int)


async def test_change_tournament_status_rejects_missing_token(client, encryption_keys, proto):
    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {"tournament_id": str(ObjectId()), "status": "Registration"},
    )

    assert payload["is_ok"] is False
    assert payload["type"] == "change_tournament_status"
    assert payload["err_code"] == "#AUTH_TOKEN_EMPTY"


async def test_change_tournament_status_rejects_invalid_token(client, encryption_keys, proto):
    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {
            "device_token": "missing-token",
            "tournament_id": str(ObjectId()),
            "status": "Registration",
        },
    )

    assert payload["is_ok"] is False
    assert payload["type"] == "change_tournament_status"
    assert payload["err_code"] == "#INSECURE_CONNECTION"


async def test_change_tournament_status_rejects_missing_required_fields(client, encryption_keys, proto):
    token = "organizer-token"
    organizer_id = ObjectId()

    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {"device_token": token, "status": "Registration"},
        tokens=user_token(client, token, organizer_id),
    )

    assert payload["is_ok"] is False
    assert payload["type"] == "change_tournament_status"
    assert payload["err_code"] == "#INCOMPLETE_REQUEST"


async def test_change_tournament_status_rejects_non_organizer(client, encryption_keys, proto):
    token = "team-token"
    user_id = ObjectId()
    db = FakeDb(users=db_user(user_id, role="team"))

    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {
            "device_token": token,
            "tournament_id": str(ObjectId()),
            "status": "Registration",
        },
        db=db,
        tokens=user_token(client, token, user_id, role="team"),
    )

    assert payload["is_ok"] is False
    assert payload["type"] == "change_tournament_status"
    assert payload["err_code"] == "#FORBIDDEN"


async def test_change_tournament_status_rejects_different_organizer(client, encryption_keys, proto):
    token = "organizer-token"
    tournament_id = ObjectId()
    owner_id = ObjectId()
    other_organizer_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": owner_id,
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [],
                }
            }
        ),
        users=db_user(other_organizer_id),
    )

    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {
            "device_token": token,
            "tournament_id": str(tournament_id),
            "status": "Registration",
        },
        db=db,
        tokens=user_token(client, token, other_organizer_id),
    )

    assert payload["is_ok"] is False
    assert payload["type"] == "change_tournament_status"
    assert payload["err_code"] == "#FORBIDDEN"


async def test_change_tournament_status_rejects_invalid_tournament_id(client, encryption_keys, proto):
    token = "organizer-token"
    organizer_id = ObjectId()
    db = FakeDb(users=db_user(organizer_id))

    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {
            "device_token": token,
            "tournament_id": "not-an-object-id",
            "status": "Registration",
        },
        db=db,
        tokens=user_token(client, token, organizer_id),
    )

    assert payload["is_ok"] is False
    assert payload["type"] == "change_tournament_status"
    assert payload["err_code"] == "#INVALID_ID"


async def test_change_tournament_status_rejects_missing_tournament(client, encryption_keys, proto):
    token = "organizer-token"
    organizer_id = ObjectId()
    db = FakeDb(users=db_user(organizer_id))

    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {
            "device_token": token,
            "tournament_id": str(ObjectId()),
            "status": "Registration",
        },
        db=db,
        tokens=user_token(client, token, organizer_id),
    )

    assert payload["is_ok"] is False
    assert payload["type"] == "change_tournament_status"
    assert payload["err_code"] == "#NOT_FOUND"


async def test_change_tournament_status_rejects_invalid_status(client, encryption_keys, proto):
    token = "organizer-token"
    organizer_id = ObjectId()
    db = FakeDb(users=db_user(organizer_id))

    payload = await call_handler(
        client,
        encryption_keys,
        proto,
        {
            "device_token": token,
            "tournament_id": str(ObjectId()),
            "status": "Published",
        },
        db=db,
        tokens=user_token(client, token, organizer_id),
    )

    assert payload["is_ok"] is False
    assert payload["type"] == "change_tournament_status"
    assert payload["err_code"] == "#INVALID_STATUS"
