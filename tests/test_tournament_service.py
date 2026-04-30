import pytest
from bson import ObjectId

from services.tournament_service import TournamentService


class FakeTournamentCollection:
    def __init__(self):
        self.insert_one_calls = []

    async def insert_one(self, document):
        self.insert_one_calls.append(document)
        return type("InsertResult", (), {"inserted_id": ObjectId()})()


class FakeDb:
    def __init__(self):
        self.tournaments = FakeTournamentCollection()

    def __getitem__(self, name):
        assert name == "tournaments"
        return self.tournaments


@pytest.mark.asyncio
async def test_create_tournament_for_admin_returns_serialized_tournament():
    db = FakeDb()
    user_id = ObjectId()

    result = await TournamentService.create_tournament(
        db=db,
        data={"title": "Spring Cup", "description": "Test event"},
        user={"_id": user_id, "role": "admin"},
    )

    assert result["title"] == "Spring Cup"
    assert result["description"] == "Test event"
    assert result["created_by"] == str(user_id)
    assert result["status"] == "Draft"
    assert isinstance(result["_id"], str)
    assert db.tournaments.insert_one_calls[0]["title"] == "Spring Cup"


@pytest.mark.asyncio
async def test_create_tournament_rejects_non_admin():
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
            user={"_id": ObjectId(), "role": "admin"},
        )
