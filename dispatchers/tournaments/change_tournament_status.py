from typing import TYPE_CHECKING, Any

from fastapi import WebSocket
from services.tournament_service import TournamentService

if TYPE_CHECKING:
    import dispatchers.utils.FGProto as FGProto
else:
    FGProto = Any


MESSAGE_TYPE = "change_tournament_status"


ERRORS = {
    "Access denied": ("You do not have permission to perform this action.", "FORBIDDEN"),
    "Required data is missing": (
        "Required data is missing. Please check your request and try again.",
        "INCOMPLETE_REQUEST",
    ),
    "Invalid tournament_id": (
        "Invalid ID provided. Please check your request and try again.",
        "INVALID_ID",
    ),
    "Tournament not found": ("The requested resource was not found.", "NOT_FOUND"),
}


async def send_change_status_error(client, proto, ENCRYPTION_KEYS, message, error_code):
    await proto.send_message(
        {
            "is_ok": False,
            "type": MESSAGE_TYPE,
            "error": message,
            "err_code": f"#{error_code}",
        },
        ENCRYPTION_KEYS[client]["key"],
        client_usr=client,
    )


def map_change_status_error(error):
    message = str(error)
    if message.startswith("Invalid status."):
        return message, "INVALID_STATUS"

    return ERRORS.get(message, (message, "BAD_REQUEST"))


async def change_tournament_status(
    client: WebSocket, 
    message: dict, 
    db: any,
    USER_TOKENS: dict, 
    proto: FGProto, 
    ENCRYPTION_KEYS: dict
) -> None:

    if not isinstance(message.get("device_token"), str):
        await send_change_status_error(
            client,
            proto,
            ENCRYPTION_KEYS,
            "Authorization token is missing. Please try again later.",
            "AUTH_TOKEN_EMPTY",
        )
        return

    if not (message["device_token"] in USER_TOKENS and USER_TOKENS[message["device_token"]][0] == client):
        await send_change_status_error(
            client,
            proto,
            ENCRYPTION_KEYS,
            "Unable to establish a secure connection. Please try again later.",
            "INSECURE_CONNECTION",
        )
        return

    if not message.get("tournament_id") or not message.get("status"):
        await send_change_status_error(
            client,
            proto,
            ENCRYPTION_KEYS,
            "Required data is missing. Please check your request and try again.",
            "INCOMPLETE_REQUEST",
        )
        return

    user = USER_TOKENS[message["device_token"]][1]
    db_user = await db["users"].find_one({"_id": user["_id"]}, {"role": 1})

    if not db_user or db_user.get("role") != "organizer":
        await send_change_status_error(
            client,
            proto,
            ENCRYPTION_KEYS,
            "You do not have permission to perform this action.",
            "FORBIDDEN",
        )
        return

    try:
        service_user = {**user, "role": db_user["role"]}
        tournament = await TournamentService.change_tournament_status(
            db=db,
            tournament_id=message["tournament_id"],
            status=message["status"],
            user=service_user,
        )
    except Exception as error:
        error_message, error_code = map_change_status_error(error)
        await send_change_status_error(
            client,
            proto,
            ENCRYPTION_KEYS,
            error_message,
            error_code,
        )
        return

    await proto.send_message(
        {"is_ok": True, 
         "type": MESSAGE_TYPE, 
         "tournament": tournament
         },
        ENCRYPTION_KEYS[client]["key"],
    )
