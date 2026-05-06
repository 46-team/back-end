MESSAGE_TYPE = "get_actual_tournaments"


async def get_actual_tournaments_handler(client, message, db, USER_TOKENS, proto, ENCRYPTION_KEYS):
    token = message.get("device_token")

    if token not in USER_TOKENS or USER_TOKENS[token][0] != client:
        await proto.send_message(
            {
                "is_ok": False,
                "type": MESSAGE_TYPE,
                "error": "Invalid token"
            },
            ENCRYPTION_KEYS[client]["key"]
        )
        return

    from services.tournament_service import TournamentService

    try:
        user = USER_TOKENS[token][1]
        tournaments = await TournamentService.get_actual_tournaments(db, user)

        await proto.send_message(
            {
                "is_ok": True,
                "type": MESSAGE_TYPE,
                "tournaments": tournaments
            },
            ENCRYPTION_KEYS[client]["key"]
        )

    except Exception as e:
        await proto.send_message(
            {
                "is_ok": False,
                "type": MESSAGE_TYPE,
                "error": str(e)
            },
            ENCRYPTION_KEYS[client]["key"]
        )
