from typing import TYPE_CHECKING, Any

from fastapi import WebSocket
from bson import ObjectId
from bson.errors import InvalidId
from dispatchers.utils.error_templates import (
    err_incompl_request,
    err_invalid_id,
    err_not_found,
    err_empty_token,
    err_invalid_token,
)
from services.tournament_service import get_tournament as tournament_service_get

if TYPE_CHECKING:
    import dispatchers.utils.FGProto as FGProto
else:
    FGProto = Any


async def get_tournament(
    client: WebSocket,
    message: dict,
    db: any,
    USER_TOKENS: dict,
    proto: FGProto,
    ENCRYPTION_KEYS: dict
) -> None:
    token = message.get("device_token")

    if not isinstance(token, str):
        await err_empty_token(
            proto=proto,
            ENCRYPTION_KEYS=ENCRYPTION_KEYS,
            client=client
        )
        return

    if token not in USER_TOKENS or USER_TOKENS[token][0] != client:
        await err_invalid_token(
            proto=proto,
            ENCRYPTION_KEYS=ENCRYPTION_KEYS,
            client=client,
            type="get_tournament",
        )
        return

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
            client=client,
            type="get_tournament"
        )
        return

    tournament = await tournament_service_get(db, oid)

    if not tournament:
        await err_not_found(
            proto=proto,
            ENCRYPTION_KEYS=ENCRYPTION_KEYS,
            client=client,
            type="get_tournament"
        )
        return

    await proto.send_message(
        {
            "is_ok": True,
            "type": "get_tournament",
            "tournament": tournament
        },
        ENCRYPTION_KEYS[client]["key"],
    )
