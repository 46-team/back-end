from bson import ObjectId

PUBLIC_USER_FIELDS = {"_id", "email", "full_name", "login", "role"}


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


def serialize_public_user(document):
    raw_document = dict(document)
    public_user = {
        key: raw_document[key]
        for key in PUBLIC_USER_FIELDS
        if key in raw_document
    }
    return serialize_mongo_value(public_user)
