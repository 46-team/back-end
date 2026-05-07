from bson import ObjectId

from dispatchers.utils.serializers import serialize_mongo_document, serialize_public_user


def test_serialize_mongo_document_converts_nested_object_ids():
    inner_id = ObjectId()
    outer_id = ObjectId()

    result = serialize_mongo_document(
        {
            "_id": outer_id,
            "items": [{"nested_id": inner_id}],
        }
    )

    assert result == {
        "_id": str(outer_id),
        "items": [{"nested_id": str(inner_id)}],
    }


def test_serialize_public_user_returns_public_fields_only():
    user_id = ObjectId()

    result = serialize_public_user(
        {
            "_id": user_id,
            "email": "bob@example.com",
            "full_name": "Bob Example",
            "login": "bob",
            "role": "team",
            "password": "secret",
            "reset_token": "private",
        }
    )

    assert result == {
        "_id": str(user_id),
        "email": "bob@example.com",
        "full_name": "Bob Example",
        "login": "bob",
        "role": "team",
    }
