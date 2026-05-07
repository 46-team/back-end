import re

from bson import ObjectId

from dispatchers.authentication.search_users import search_users_handler


class FakeAsyncCursor:
    def __init__(self, documents):
        self.documents = documents
        self.limit_value = None

    def limit(self, value):
        self.limit_value = value
        self.documents = self.documents[:value]
        return self

    def __aiter__(self):
        self._iterator = iter(self.documents)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration


class FakeUsersCollection:
    def __init__(self, documents):
        self.documents = documents
        self.find_calls = []

    def find(self, query, projection=None):
        self.find_calls.append((query, projection))
        documents = [
            self._apply_projection(document, projection)
            for document in self.documents
            if self._matches_query(document, query)
        ]
        return FakeAsyncCursor(documents)

    def _apply_projection(self, document, projection):
        if not projection:
            return dict(document)

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

            if key == "$or":
                if not any(self._matches_query(document, item) for item in expected):
                    return False
                continue

            actual = document.get(key)
            if isinstance(expected, dict):
                if "$in" in expected:
                    if actual not in expected["$in"]:
                        return False
                    continue

                if "$regex" in expected:
                    flags = re.IGNORECASE if expected.get("$options") == "i" else 0
                    if not re.search(expected["$regex"], str(actual or ""), flags):
                        return False
                    continue

            if actual != expected:
                return False

        return True


class FakeDb:
    def __init__(self, users):
        self.users = users

    def __getitem__(self, name):
        if name == "users":
            return self.users

        raise KeyError(name)


async def test_search_users_allows_admin_role_management(client, encryption_keys, proto):
    first_id = ObjectId()
    second_id = ObjectId()
    users = FakeUsersCollection(
        [
            {
                "_id": first_id,
                "email": "alice@example.com",
                "full_name": "Alice Example",
                "login": "alice",
                "role": "admin",
                "password": "secret",
            },
            {
                "_id": second_id,
                "email": "bob@example.com",
                "full_name": "Bob Example",
                "login": "bob",
                "role": "team",
                "private_note": "hidden",
            },
        ]
    )
    token = "admin-token"

    await search_users_handler(
        client=client,
        message={"device_token": token, "purpose": "role_management", "query": "example"},
        db=FakeDb(users),
        USER_TOKENS={token: [client, {"_id": ObjectId(), "role": "admin"}, False, "login", {}]},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert payload["type"] == "search_users"
    assert [user["_id"] for user in payload["users"]] == [str(first_id), str(second_id)]
    assert all("password" not in user for user in payload["users"])
    assert all("private_note" not in user for user in payload["users"])


async def test_search_users_allows_organizer_tournament_participants_only(client, encryption_keys, proto):
    team_id = ObjectId()
    jury_id = ObjectId()
    admin_id = ObjectId()
    users = FakeUsersCollection(
        [
            {"_id": team_id, "email": "team@example.com", "full_name": "Team One", "login": "team", "role": "team"},
            {"_id": jury_id, "email": "jury@example.com", "full_name": "Jury One", "login": "jury", "role": "jury"},
            {
                "_id": admin_id,
                "email": "admin@example.com",
                "full_name": "Admin One",
                "login": "admin",
                "role": "admin",
            },
        ]
    )
    token = "organizer-token"

    await search_users_handler(
        client=client,
        message={"device_token": token, "purpose": "tournament_participants"},
        db=FakeDb(users),
        USER_TOKENS={token: [client, {"_id": ObjectId(), "role": "organizer"}, False, "login", {}]},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is True
    assert [user["_id"] for user in payload["users"]] == [str(team_id), str(jury_id)]


async def test_search_users_rejects_unauthenticated_access(client, encryption_keys, proto):
    await search_users_handler(
        client=client,
        message={"device_token": "missing-token", "purpose": "role_management"},
        db=FakeDb(FakeUsersCollection([])),
        USER_TOKENS={},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "search_users"
    assert payload["error"] == "Authentication required"


async def test_search_users_rejects_wrong_role(client, encryption_keys, proto):
    token = "team-token"

    await search_users_handler(
        client=client,
        message={"device_token": token, "purpose": "role_management"},
        db=FakeDb(FakeUsersCollection([])),
        USER_TOKENS={token: [client, {"_id": ObjectId(), "role": "team"}, False, "login", {}]},
        proto=proto,
        ENCRYPTION_KEYS=encryption_keys,
    )

    payload, _ = proto.send_message.await_args.args
    assert payload["is_ok"] is False
    assert payload["type"] == "search_users"
    assert payload["error"] == "Access denied"
