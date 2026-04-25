from bson import ObjectId


def serialize_mongo_value(value):
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, dict):
        return {key: serialize_mongo_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [serialize_mongo_value(item) for item in value]

    return value


def serialize_mongo_document(document):
    return serialize_mongo_value(dict(document))
