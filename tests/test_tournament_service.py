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

    def find(self, query, projection=None):
        documents = [
            self._apply_projection(document, projection)
            for document in self.documents.values()
            if self._matches_query(document, query)
        ]
        return FakeAsyncCursor(documents)

    async def update_one(self, query, update):
        self.update_one_calls.append((query, update))
        document = self.documents.get(query["_id"])
        if document:
            document.update(update.get("$set", {}))

    def _apply_projection(self, document, projection):
        if not projection:
            return document

        return {
            key: value
            for key, value in document.items()
            if projection.get(key)
        }

    def _matches_query(self, document, query):
        if not query:
            return True

        for key, expected in query.items():
            if key == "$and":
                if not all(self._matches_query(document, item) for item in expected):
                    return False
                continue

            actual = document.get(key)
            if isinstance(expected, dict):
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                continue

            if isinstance(actual, list):
                if expected not in actual:
                    return False
                continue

            if actual != expected:
                return False

        return True


class FakeAsyncCursor:
    def __init__(self, documents):
        self.documents = documents

    def __aiter__(self):
        self._iterator = iter(self.documents)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration


class FakeUsersCollection:
    def __init__(self, documents=None):
        self.documents = documents or {}

    async def find_one(self, query, projection=None):
        document = self.documents.get(query["_id"])
        if not document or not projection:
            return document

        return {
            key: value
            for key, value in document.items()
            if projection.get(key)
        }


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
    participant_id = ObjectId()
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
                    "participant_ids": [participant_id],
                }
            }
        ),
        users=FakeUsersCollection(
            {
                participant_id: {
                    "_id": participant_id,
                    "email": "participant@example.com",
                    "full_name": "Participant User",
                    "login": "participant",
                    "role": "team",
                    "password": "secret",
                    "device_tokens": ["private-token"],
                }
            }
        ),
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
        "participants": [
            {
                "_id": str(participant_id),
                "email": "participant@example.com",
                "full_name": "Participant User",
                "login": "participant",
                "role": "team",
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_tournament_returns_empty_participants_when_none_assigned():
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

    result = await get_tournament(db, tournament_id)

    assert result["participants"] == []
    assert "participant_ids" not in result


@pytest.mark.asyncio
async def test_get_tournament_skips_missing_participant_users():
    tournament_id = ObjectId()
    existing_participant_id = ObjectId()
    missing_participant_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": ObjectId(),
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [existing_participant_id, missing_participant_id],
                }
            }
        ),
        users=FakeUsersCollection(
            {
                existing_participant_id: {
                    "_id": existing_participant_id,
                    "email": "existing@example.com",
                    "full_name": "Existing User",
                    "login": "existing",
                    "role": "team",
                    "password": "secret",
                }
            }
        ),
    )

    result = await get_tournament(db, tournament_id)

    assert result["participants"] == [
        {
            "_id": str(existing_participant_id),
            "email": "existing@example.com",
            "full_name": "Existing User",
            "login": "existing",
            "role": "team",
        }
    ]
    assert "participant_ids" not in result


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
    assert db.tournaments.insert_one_calls[0]["start_date"] is None
    assert db.tournaments.insert_one_calls[0]["end_date"] is None


@pytest.mark.asyncio
async def test_create_tournament_accepts_valid_dates():
    db = FakeDb()
    user_id = ObjectId()

    result = await TournamentService.create_tournament(
        db=db,
        data={
            "title": "Spring Cup",
            "start_date": "2026-05-10T10:00:00",
            "end_date": "2026-05-11T10:00:00",
        },
        user={"_id": user_id, "role": "organizer"},
    )

    assert result["start_date"] == "2026-05-10T10:00:00"
    assert result["end_date"] == "2026-05-11T10:00:00"
    assert db.tournaments.insert_one_calls[0]["start_date"] == "2026-05-10T10:00:00"
    assert db.tournaments.insert_one_calls[0]["end_date"] == "2026-05-11T10:00:00"


@pytest.mark.asyncio
async def test_create_tournament_rejects_invalid_date_format():
    db = FakeDb()

    with pytest.raises(Exception, match="Invalid tournament dates"):
        await TournamentService.create_tournament(
            db=db,
            data={
                "title": "Spring Cup",
                "start_date": "not-a-date",
                "end_date": "2026-05-11T10:00:00",
            },
            user={"_id": ObjectId(), "role": "organizer"},
        )

    assert db.tournaments.insert_one_calls == []


@pytest.mark.asyncio
async def test_create_tournament_rejects_equal_dates():
    db = FakeDb()

    with pytest.raises(Exception, match="start_date"):
        await TournamentService.create_tournament(
            db=db,
            data={
                "title": "Spring Cup",
                "start_date": "2026-05-10T10:00:00",
                "end_date": "2026-05-10T10:00:00",
            },
            user={"_id": ObjectId(), "role": "organizer"},
        )

    assert db.tournaments.insert_one_calls == []


@pytest.mark.asyncio
async def test_create_tournament_rejects_start_date_after_end_date():
    db = FakeDb()

    with pytest.raises(Exception, match="start_date"):
        await TournamentService.create_tournament(
            db=db,
            data={
                "title": "Spring Cup",
                "start_date": "2026-05-12T10:00:00",
                "end_date": "2026-05-11T10:00:00",
            },
            user={"_id": ObjectId(), "role": "organizer"},
        )

    assert db.tournaments.insert_one_calls == []


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
async def test_get_actual_tournaments_for_participant_returns_assigned_tournaments_only():
    participant_id = ObjectId()
    other_participant_id = ObjectId()
    organizer_id = ObjectId()
    assigned_tournament_id = ObjectId()
    unassigned_tournament_id = ObjectId()
    archived_tournament_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                assigned_tournament_id: {
                    "_id": assigned_tournament_id,
                    "title": "Assigned Cup",
                    "created_by": organizer_id,
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [participant_id],
                },
                unassigned_tournament_id: {
                    "_id": unassigned_tournament_id,
                    "title": "Other Cup",
                    "created_by": organizer_id,
                    "status": "Draft",
                    "created_at": 1710000001,
                    "participant_ids": [other_participant_id],
                },
                archived_tournament_id: {
                    "_id": archived_tournament_id,
                    "title": "Archived Cup",
                    "created_by": organizer_id,
                    "status": "Archived",
                    "created_at": 1710000002,
                    "participant_ids": [participant_id],
                },
            }
        )
    )

    result = await TournamentService.get_actual_tournaments(
        db=db,
        user={"_id": participant_id, "role": "team"},
    )

    assert [tournament["_id"] for tournament in result] == [str(assigned_tournament_id)]
    assert "participant_ids" not in result[0]


@pytest.mark.asyncio
async def test_get_actual_tournaments_for_organizer_returns_created_tournaments_only():
    organizer_id = ObjectId()
    other_organizer_id = ObjectId()
    created_tournament_id = ObjectId()
    other_tournament_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                created_tournament_id: {
                    "_id": created_tournament_id,
                    "title": "Created Cup",
                    "created_by": organizer_id,
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [],
                },
                other_tournament_id: {
                    "_id": other_tournament_id,
                    "title": "Other Organizer Cup",
                    "created_by": other_organizer_id,
                    "status": "Draft",
                    "created_at": 1710000001,
                    "participant_ids": [organizer_id],
                },
            }
        )
    )

    result = await TournamentService.get_actual_tournaments(
        db=db,
        user={"_id": organizer_id, "role": "organizer"},
    )

    assert [tournament["_id"] for tournament in result] == [str(created_tournament_id)]


@pytest.mark.asyncio
async def test_get_actual_tournaments_for_admin_returns_all_actual_tournaments():
    organizer_id = ObjectId()
    actual_tournament_id = ObjectId()
    archived_tournament_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                actual_tournament_id: {
                    "_id": actual_tournament_id,
                    "title": "Actual Cup",
                    "created_by": organizer_id,
                    "status": "Draft",
                    "created_at": 1710000000,
                    "participant_ids": [],
                },
                archived_tournament_id: {
                    "_id": archived_tournament_id,
                    "title": "Archived Cup",
                    "created_by": organizer_id,
                    "status": "Archived",
                    "created_at": 1710000001,
                    "participant_ids": [],
                },
            }
        )
    )

    result = await TournamentService.get_actual_tournaments(
        db=db,
        user={"_id": ObjectId(), "role": "admin"},
    )

    assert [tournament["_id"] for tournament in result] == [str(actual_tournament_id)]


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


@pytest.mark.asyncio
async def test_update_tournament_for_organizer_updates_allowed_fields():
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

    result = await TournamentService.update_tournament(
        db=db,
        tournament_id=str(tournament_id),
        data={
            "title": "Summer Cup",
            "description": "New description",
            "start_date": "2026-05-11",
            "end_date": "2026-05-13",
            "status": "Published",
        },
        user={"_id": organizer_id, "role": "organizer"},
    )

    assert result["_id"] == str(tournament_id)
    assert result["title"] == "Summer Cup"
    assert result["description"] == "New description"
    assert result["start_date"] == "2026-05-11"
    assert result["end_date"] == "2026-05-13"
    assert result["status"] == "Draft"
    assert isinstance(result["updated_at"], int)

    update = db.tournaments.update_one_calls[0][1]["$set"]
    assert update["title"] == "Summer Cup"
    assert update["description"] == "New description"
    assert update["start_date"] == "2026-05-11"
    assert update["end_date"] == "2026-05-13"
    assert "status" not in update
    assert isinstance(update["updated_at"], int)


@pytest.mark.asyncio
async def test_update_tournament_rejects_non_organizer():
    db = FakeDb()

    with pytest.raises(Exception, match="Access denied"):
        await TournamentService.update_tournament(
            db=db,
            tournament_id=str(ObjectId()),
            data={"title": "Summer Cup"},
            user={"_id": ObjectId(), "role": "team"},
        )


@pytest.mark.asyncio
async def test_update_tournament_requires_tournament_id():
    db = FakeDb()

    with pytest.raises(Exception, match="Required data is missing"):
        await TournamentService.update_tournament(
            db=db,
            tournament_id=None,
            data={"title": "Summer Cup"},
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_update_tournament_rejects_invalid_tournament_id():
    db = FakeDb()

    with pytest.raises(Exception, match="Invalid tournament_id"):
        await TournamentService.update_tournament(
            db=db,
            tournament_id="not-an-object-id",
            data={"title": "Summer Cup"},
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_update_tournament_rejects_missing_tournament():
    db = FakeDb()

    with pytest.raises(Exception, match="Tournament not found"):
        await TournamentService.update_tournament(
            db=db,
            tournament_id=str(ObjectId()),
            data={"title": "Summer Cup"},
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_update_tournament_rejects_different_organizer():
    tournament_id = ObjectId()
    tournament_owner_id = ObjectId()
    other_organizer_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": tournament_owner_id,
                    "start_date": "2026-05-10",
                    "end_date": "2026-05-12",
                    "status": "Draft",
                    "created_at": 1710000000,
                }
            }
        )
    )

    with pytest.raises(Exception, match="Access denied"):
        await TournamentService.update_tournament(
            db=db,
            tournament_id=str(tournament_id),
            data={"title": "Summer Cup"},
            user={"_id": other_organizer_id, "role": "organizer"},
        )

    assert db.tournaments.update_one_calls == []


@pytest.mark.asyncio
async def test_update_tournament_rejects_empty_title():
    tournament_id = ObjectId()
    organizer_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": organizer_id,
                    "start_date": "2026-05-10",
                    "end_date": "2026-05-12",
                    "status": "Draft",
                    "created_at": 1710000000,
                }
            }
        )
    )

    with pytest.raises(Exception, match="title"):
        await TournamentService.update_tournament(
            db=db,
            tournament_id=str(tournament_id),
            data={"title": "   "},
            user={"_id": organizer_id, "role": "organizer"},
        )

    assert db.tournaments.update_one_calls == []


@pytest.mark.asyncio
async def test_update_tournament_rejects_invalid_date_order():
    tournament_id = ObjectId()
    organizer_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
            {
                tournament_id: {
                    "_id": tournament_id,
                    "title": "Spring Cup",
                    "created_by": organizer_id,
                    "start_date": "2026-05-10",
                    "end_date": "2026-05-12",
                    "status": "Draft",
                    "created_at": 1710000000,
                }
            }
        )
    )

    with pytest.raises(Exception, match="start_date"):
        await TournamentService.update_tournament(
            db=db,
            tournament_id=str(tournament_id),
            data={"start_date": "2026-05-13"},
            user={"_id": organizer_id, "role": "organizer"},
        )

    assert db.tournaments.update_one_calls == []


@pytest.mark.asyncio
async def test_change_tournament_status_for_owner_updates_status_and_timestamp():
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

    result = await TournamentService.change_tournament_status(
        db=db,
        tournament_id=str(tournament_id),
        status="Registration",
        user={"_id": organizer_id, "role": "organizer"},
    )

    assert result["_id"] == str(tournament_id)
    assert result["status"] == "Registration"
    assert isinstance(result["updated_at"], int)

    update = db.tournaments.update_one_calls[0][1]["$set"]
    assert update["status"] == "Registration"
    assert isinstance(update["updated_at"], int)


@pytest.mark.asyncio
async def test_change_tournament_status_rejects_non_organizer():
    db = FakeDb()

    with pytest.raises(Exception, match="Access denied"):
        await TournamentService.change_tournament_status(
            db=db,
            tournament_id=str(ObjectId()),
            status="Registration",
            user={"_id": ObjectId(), "role": "team"},
        )


@pytest.mark.asyncio
async def test_change_tournament_status_rejects_different_organizer():
    tournament_id = ObjectId()
    tournament_owner_id = ObjectId()
    other_organizer_id = ObjectId()
    db = FakeDb(
        tournaments=FakeTournamentCollection(
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
    )

    with pytest.raises(Exception, match="Access denied"):
        await TournamentService.change_tournament_status(
            db=db,
            tournament_id=str(tournament_id),
            status="Registration",
            user={"_id": other_organizer_id, "role": "organizer"},
        )

    assert db.tournaments.update_one_calls == []


@pytest.mark.asyncio
async def test_change_tournament_status_rejects_invalid_tournament_id():
    db = FakeDb()

    with pytest.raises(Exception, match="Invalid tournament_id"):
        await TournamentService.change_tournament_status(
            db=db,
            tournament_id="not-an-object-id",
            status="Registration",
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_change_tournament_status_rejects_missing_tournament():
    db = FakeDb()

    with pytest.raises(Exception, match="Tournament not found"):
        await TournamentService.change_tournament_status(
            db=db,
            tournament_id=str(ObjectId()),
            status="Registration",
            user={"_id": ObjectId(), "role": "organizer"},
        )


@pytest.mark.asyncio
async def test_change_tournament_status_rejects_invalid_status():
    db = FakeDb()

    with pytest.raises(Exception, match="Invalid status"):
        await TournamentService.change_tournament_status(
            db=db,
            tournament_id=str(ObjectId()),
            status="Published",
            user={"_id": ObjectId(), "role": "organizer"},
        )
