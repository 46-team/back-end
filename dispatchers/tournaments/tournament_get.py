from fastapi import WebSocket
from bson import ObjectId
from services.tournament_service import serialize_mongo_document
from bson.errors import InvalidId
import dispatchers.utils.FGProto as FGProto
from dispatchers.utils.error_templates import (
    err_incompl_request,
    err_invalid_id,
    err_not_found,
    err_empty_token,
    err_invalid_token,
)


TOURNAMENT_FIELDS = {
    "_id": 1,
    "title": 1,
    "description": 1,
    "created_by": 1,
    "start_date": 1,
    "end_date": 1,
    "status": 1,
    "created_at": 1,
}


async def get_tournament(
    client: WebSocket, 
    message: dict, 
    db: any,
    USER_TOKENS: dict, 
    proto: FGProto, 
    ENCRYPTION_KEYS: dict
) -> None:
    if not isinstance(message.get("token"), str):
        await err_empty_token(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client
            )
        return

    if not (message["token"] in USER_TOKENS and USER_TOKENS[message["token"]][0] == client):
        await err_invalid_token(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client)
        return

    if not message.get("tournament_id"):
        await err_incompl_request(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client)
        return

    try:
        oid = ObjectId(message["tournament_id"])
    except (InvalidId, TypeError):
        await err_invalid_id(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client)
        return

    doc = await db["tournaments"].find_one({"_id": oid}, TOURNAMENT_FIELDS)

    if not doc:
        await err_not_found(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client, 
            entity="tournament")
        return

    await proto.send_message(
        {
            "is_ok": True, 
            "type": "get_tournament", 
            "tournament": serialize_mongo_document(doc)},
        ENCRYPTION_KEYS[client]["key"],
    )