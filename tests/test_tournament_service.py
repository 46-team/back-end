import pytest
from bson import ObjectId

from services.tournament_service import TournamentService, get_tournament


class FakeTournamentCollection:
    def __init__(self, documents=None):
        self.insert_one_calls = []
        self.update_one_calls = []
        self.documents = documents or {}

    async def insert_one(self, document):
        self.insert_one_calls.append(document)
        return type("InsertResult", (), {"inserted_id": ObjectId()})()

    async def find_one(self, query, projection=None):
        document = self.documents.get(query["_id"])
        if not document or not projection:
            return document

        return {
            key: value
            for key, value in document.items()
            if projection.get(key)
        }

    async def update_one(self, query, update):
        self.update_one_calls.append((query, update))
        document = self.documents.get(query["_id"])
        if document:
            document.update(update.get("$set", {}))


class FakeUsersCollection:
    def __init__(self, documents=None):
        self.documents = documents or {}

    async def find_one(self, query):
        return self.documents.get(query["_id"])


class FakeDb:
    def __init__(self, tournaments=None, users=None):
        self.tournaments = tournaments or FakeTournamentCollection()
        self.users = users or FakeUsersCollection()

    def __getitem__(self, name):
        if name == "tournaments":
            return self.tournaments

        if name == "users":
            return self.users

        raise KeyError(name)


@pytest.mark.asyncio
async def test_get_tournament_returns_serialized_public_fields_only():
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
                    "start_date": "2026-05-10",
                    "end_date": "2026-05-11",
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [ObjectId()],
                }
            }
        )
    )

    result = await get_tournament(db, tournament_id)

    assert result == {
        "_id": str(tournament_id),
        "title": "Spring Cup",
        "description": "Test event",
        "created_by": str(organizer_id),
        "start_date": "2026-05-10",
        "end_date": "2026-05-11",
        "status": "Draft",
        "created_at": 1710000000,
    }


@pytest.mark.asyncio
async def test_get_tournament_returns_none_when_missing():
    result = await get_tournament(FakeDb(), ObjectId())

    assert result is None


@pytest.mark.asyncio
async def test_create_tournament_for_organizer_returns_serialized_tournament():
    db = FakeDb()
    user_id = ObjectId()

    result = await TournamentService.create_tournament(
        db=db,
        data={"title": "Spring Cup", "description": "Test event"},
        user={"_id": user_id, "role": "organizer"},
    )

    assert result["title"] == "Spring Cup"
    assert result["description"] == "Test event"
    assert result["created_by"] == str(user_id)
    assert result["participant_ids"] == []
    assert result["status"] == "Draft"
    assert isinstance(result["_id"], str)
    assert db.tournaments.insert_one_calls[0]["title"] == "Spring Cup"
    assert db.tournaments.insert_one_calls[0]["participant_ids"] == []


@pytest.mark.asyncio
async def test_create_tournament_rejects_non_organizer():
    db = FakeDb()

    with pytest.raises(Exception, match="Access denied"):
        await TournamentService.create_tournament(
            db=db,
            data={"title": "Spring Cup"},
            user={"_id": ObjectId(), "role": "team"},
        )


@pytest.mark.asyncio
async def test_create_tournament_requires_title():
    db = FakeDb()

    with pytest.raises(Exception, match="title"):
        await TournamentService.create_tournament(
            db=db,
            data={},
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_assign_participants_for_organizer_updates_tournament():
    tournament_id = ObjectId()
    organizer_id = ObjectId()
    first_user_id = ObjectId()
    second_user_id = ObjectId()
    tournaments = FakeTournamentCollection(
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
    )
    users = FakeUsersCollection(
        {
            first_user_id: {"_id": first_user_id, "role": "team"},
            second_user_id: {"_id": second_user_id, "role": "team"},
        }
    )
    db = FakeDb(tournaments=tournaments, users=users)

    result = await TournamentService.assign_participants(
        db=db,
        tournament_id=str(tournament_id),
        participant_ids=[str(first_user_id), str(second_user_id)],
        user={"_id": organizer_id, "role": "organizer"},
    )

    assert result["_id"] == str(tournament_id)
    assert result["participant_ids"] == [str(first_user_id), str(second_user_id)]
    assert tournaments.update_one_calls == [
        (
            {"_id": tournament_id},
            {"$set": {"participant_ids": [first_user_id, second_user_id]}},
        )
    ]


@pytest.mark.asyncio
async def test_assign_participants_rejects_different_organizer():
    tournament_id = ObjectId()
    tournament_owner_id = ObjectId()
    other_organizer_id = ObjectId()
    tournaments = FakeTournamentCollection(
        {
            tournament_id: {
                "_id": tournament_id,
                "title": "Spring Cup",
                "created_by": tournament_owner_id,
                "status": "Draft",
                "created_at": 1710000000,
                "participant_ids": [],
            }
        }
    )
    db = FakeDb(tournaments=tournaments)

    with pytest.raises(Exception, match="Access denied"):
        await TournamentService.assign_participants(
            db=db,
            tournament_id=str(tournament_id),
            participant_ids=[],
            user={"_id": other_organizer_id, "role": "organizer"},
        )

    assert tournaments.update_one_calls == []


@pytest.mark.asyncio
async def test_assign_participants_rejects_non_organizer():
    db = FakeDb()

    with pytest.raises(Exception, match="Access denied"):
        await TournamentService.assign_participants(
            db=db,
            tournament_id=str(ObjectId()),
            participant_ids=[],
            user={"_id": ObjectId(), "role": "team"},
        )


@pytest.mark.asyncio
async def test_assign_participants_rejects_invalid_tournament_id():
    db = FakeDb()

    with pytest.raises(Exception, match="Invalid tournament_id"):
        await TournamentService.assign_participants(
            db=db,
            tournament_id="not-an-object-id",
            participant_ids=[],
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_assign_participants_rejects_missing_tournament():
    db = FakeDb()

    with pytest.raises(Exception, match="Tournament not found"):
        await TournamentService.assign_participants(
            db=db,
            tournament_id=str(ObjectId()),
            participant_ids=[],
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_assign_participants_rejects_non_list_participant_ids():
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
                    "participant_ids": [],
                }
            }
        )
    )

    with pytest.raises(Exception, match="Invalid participant_ids"):
        await TournamentService.assign_participants(
            db=db,
            tournament_id=str(tournament_id),
            participant_ids=str(ObjectId()),
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_assign_participants_rejects_invalid_user_id():
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
        )
    )

    with pytest.raises(Exception, match="Invalid user_id"):
        await TournamentService.assign_participants(
            db=db,
            tournament_id=str(tournament_id),
            participant_ids=["not-an-object-id"],
            user={"_id": organizer_id, "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_assign_participants_rejects_missing_user():
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
        )
    )

    with pytest.raises(Exception, match="User not found"):
        await TournamentService.assign_participants(
            db=db,
            tournament_id=str(tournament_id),
            participant_ids=[str(ObjectId())],
            user={"_id": organizer_id, "role": "organizer"},
        )
