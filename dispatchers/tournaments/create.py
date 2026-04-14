async def create_tournament_handler(client, message, db, USER_TOKENS, proto, ENCRYPTION_KEYS):

    token = message.get("device_token")

    if token not in USER_TOKENS:
        return

    session = USER_TOKENS[token]
    user = session[1]

    from services.tournament_service import TournamentService

    try:
        tournament = await TournamentService.create_tournament(
            db=db,
            data=message,
            user=user
        )

        await proto.send_message(
            {
                "is_ok": True,
                "type": "create_tournament",
                "tournament": tournament
            },
            ENCRYPTION_KEYS[client]['key']
        )

    except Exception as e:
        await proto.send_message(
            {
                "is_ok": False,
                "type": "create_tournament",
                "error": str(e)
            },
            ENCRYPTION_KEYS[client]['key']
        )