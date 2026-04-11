import dispatchers.utils.FGProto as FGProto
from fastapi import WebSocket
from dispatchers.utils.dotenv_dispatcher import env_data


async def err_unknown_mode(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket, type="null") -> None:
    proto.Error(
        proto=proto,
        message="Internal server error. Please try again later.",
        enc_key=ENCRYPTION_KEYS[client]['key'],
        error_code="PROHIBITED_METHOD",
        client=client,
        type=type
    )


async def err_invalid_token(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket, type="null") -> None:
    proto.Error(
        proto=proto,
        message="Unable to establish a secure connection. Please try again later.",
        enc_key=ENCRYPTION_KEYS[client]['key'],
        error_code="INSECURE_CONNECTION",
        client=client,
        type=type
    )


async def err_empty_token(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket) -> None:
    proto.Error(
        proto,
        "Authorization token is missing. Please try again later.",
        ENCRYPTION_KEYS[client]['key'],
        "AUTH_TOKEN_EMPTY"
    )


async def err_incompl_request(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket) -> None:
    proto.Error(
        proto,
        "Required data is missing. Please check your request and try again.",
        ENCRYPTION_KEYS[client]['key'],
        "INCOMPLETE_REQUEST"
    )


async def err_db_incr(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket) -> None:
    proto.Error(
        proto,
        "Internal server error. Please try again later.",
        ENCRYPTION_KEYS[client]['key'],
        "DB_INCR_SERVER_ERROR"
    )


async def err_unknown_request(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket) -> None:
    proto.Error(
        proto,
        "Request not recognized. Please verify the method and try again.",
        ENCRYPTION_KEYS[client]['key'],
        "UNKNOWN_METHOD"
    )


async def err_events_pool(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket) -> None:
    proto.Error(
        proto,
        "Unable to synchronize account data. Please try again later.",
        ENCRYPTION_KEYS[client]['key'],
        "ACCOUNT_SYNC_ERR"
    )


async def err_session_token_nf(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket, type="null") -> None:
    proto.Error(
        proto=proto,
        message="Device not recognized.",
        enc_key=ENCRYPTION_KEYS[client]['key'],
        error_code="SESSION_TOKEN_NF",
        type=type
    )


async def err_session_token_good(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket, type="null") -> None:
    proto.Error(
        proto=proto,
        message="Invalid operation for current device state.",
        enc_key=ENCRYPTION_KEYS[client]['key'],
        error_code="SESSION_TOKEN_GOOD",
        type=type
    )


async def err_session_token_expired(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket, type="null") -> None:
    proto.Error(
        proto=proto,
        message="Token expired. Please log in again.",
        enc_key=ENCRYPTION_KEYS[client]['key'],
        error_code="SESSION_TOKEN_EXPIRED",
        type=type
    )


async def err_session_token_frozen(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket) -> None:
    proto.Error(
        proto,
        "Access temporarily restricted. Please log in again.",
        ENCRYPTION_KEYS[client]['key'],
        "AUTH_TOKEN_FROZEN"
    )


async def err_not_fully_logged_in(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket) -> None:
    proto.Error(
        proto,
        "Authentication process not completed.",
        ENCRYPTION_KEYS[client]['key'],
        "NOT_FULLY_LOGGED_IN"
    )


async def err_incorrect_login(proto: FGProto, ENCRYPTION_KEYS: dict, client: WebSocket) -> None:
    proto.Error(
        proto,
        "Invalid login credentials. Please try again.",
        ENCRYPTION_KEYS[client]['key'],
        "INCORRECT_LOGIN"
    )