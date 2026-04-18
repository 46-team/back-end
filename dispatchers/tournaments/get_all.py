async def get_tournaments_handler(client, message, db, USER_TOKENS, proto, ENCRYPTION_KEYS):

    token = message.get("device_token")

    if token not in USER_TOKENS:
        await proto.send_message(
            {
                "is_ok": False,
                "type": "get_tournaments",
                "error": "Invalid token"
            },
            ENCRYPTION_KEYS[client]['key']
        )
        return

    from services.tournament_service import TournamentService

    try:
        tournaments = await TournamentService.get_tournaments(db)

        await proto.send_message(
            {
                "is_ok": True,
                "type": "get_tournaments",
                "tournaments": tournaments
            },
            ENCRYPTION_KEYS[client]['key']
        )

    except Exception as e:
        await proto.send_message(
            {
                "is_ok": False,
                "type": "get_tournaments",
                "error": str(e)
            },
            ENCRYPTION_KEYS[client]['key']
        )