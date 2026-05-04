from fastapi import WebSocket
from bson import ObjectId
from bson.errors import InvalidId
import dispatchers.utils.FGProto as FGProto
from dispatchers.utils.error_templates import (
    err_empty_token,
    err_invalid_token,
    err_incompl_request,
    err_invalid_id,
    err_not_found,
)
from services.tournament_service import change_tournament_status as service_change_status, ALLOWED_STATUSES


async def change_tournament_status(
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
            client=client, 
            type="change_tournament_status"
            )
        return

   
    if not message.get("tournament_id") or not message.get("status"):
        await err_incompl_request(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client
            )
        return

    if message["status"] not in ALLOWED_STATUSES:
        proto.Error(
            proto=proto,
            message=f"Invalid status. Allowed values: {', '.join(ALLOWED_STATUSES)}.",
            enc_key=ENCRYPTION_KEYS[client]["key"],
            error_code="INVALID_STATUS",
            client=client,
            type="change_tournament_status"
        )
        return

    user = USER_TOKENS[message["token"]][1]
    db_user = await db["users"].find_one({"_id": user["_id"]}, {"role": 1})

    if not db_user or db_user.get("role") != "organizer": 
        proto.Error(
            proto=proto,
            message="You do not have permission to perform this action.",
            enc_key=ENCRYPTION_KEYS[client]["key"],
            error_code="FORBIDDEN",
            client=client,
            type="change_tournament_status"
        )
        return

    try:
        oid = ObjectId(message["tournament_id"])
    except (InvalidId, TypeError):
        await err_invalid_id(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client, 
            type="change_tournament_status"
            )
        return

    tournament = await service_change_status(db, oid, message["status"])

    if not tournament:
        await err_not_found(
            proto=proto, 
            ENCRYPTION_KEYS=ENCRYPTION_KEYS, 
            client=client, 
            type="change_tournament_status"
            )
        return

    await proto.send_message(
        {"is_ok": True, 
         "type": "change_tournament_status", 
         "tournament": tournament
         },
        ENCRYPTION_KEYS[client]["key"],
    )