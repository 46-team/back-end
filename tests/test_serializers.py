from bson import ObjectId

from dispatchers.utils.serializers import serialize_mongo_document


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
