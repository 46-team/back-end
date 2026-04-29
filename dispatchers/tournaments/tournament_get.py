from fastapi import WebSocket
from bson import ObjectId
from bson.errors import InvalidId
import dispatchers.utils.FGProto as FGProto
from dispatchers.utils.error_templates import err_incompl_request, err_invalid_id, err_not_found

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

def _fmt(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    if doc.get("created_by"):
        doc["created_by"] = str(doc["created_by"])
    return doc


async def get_tournaments(
    client: WebSocket, message: dict, db: any,
    proto: FGProto, ENCRYPTION_KEYS: dict
) -> None:
    cursor = db["tournaments"].find({}, TOURNAMENT_FIELDS)
    tournaments = [_fmt(doc) async for doc in cursor]

    await proto.send_message(
        {
          "is_ok": True,
          "type": "get_tournaments", 
          "tournaments": tournaments
        },
        ENCRYPTION_KEYS[client]["key"],
    )


async def get_tournament(
    client: WebSocket, message: dict, db: any,
    proto: FGProto, ENCRYPTION_KEYS: dict
) -> None:
    if not message.get("tournament_id"):
        await err_incompl_request(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client
            )
        return

    try:
        oid = ObjectId(message["tournament_id"])
    except (InvalidId, TypeError):
        await err_invalid_id(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client
            )
        return

    doc = await db["tournaments"].find_one({"_id": oid}, TOURNAMENT_FIELDS)

    if not doc:
        await err_not_found(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client, 
            entity="tournaments"
            )
        return

    await proto.send_message(
        {
            "is_ok": True, 
            "type": "get_tournament", 
            "tournament": _fmt(doc)
        },
        ENCRYPTION_KEYS[client]["key"],
    )