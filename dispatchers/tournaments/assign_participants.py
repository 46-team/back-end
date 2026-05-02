MESSAGE_TYPE = "assign_tournament_participants"


async def send_assign_participants_error(client, proto, ENCRYPTION_KEYS, error):
    await proto.send_message(
        {
            "is_ok": False,
            "type": MESSAGE_TYPE,
            "error": error
        },
        ENCRYPTION_KEYS[client]['key']
    )


async def assign_tournament_participants_handler(client, message, db, USER_TOKENS, proto, ENCRYPTION_KEYS):
    token = message.get("device_token")

    if not token or token not in USER_TOKENS:
        await send_assign_participants_error(client, proto, ENCRYPTION_KEYS, "Authentication required")
        return

    session = USER_TOKENS[token]
    user = session[1]

    from services.tournament_service import TournamentService

    try:
        tournament = await TournamentService.assign_participants(
            db=db,
            tournament_id=message.get("tournament_id"),
            participant_ids=message.get("participant_ids"),
            user=user
        )

        await proto.send_message(
            {
                "is_ok": True,
                "type": MESSAGE_TYPE,
                "tournament": tournament
            },
            ENCRYPTION_KEYS[client]['key']
        )

    except Exception as e:
        await send_assign_participants_error(client, proto, ENCRYPTION_KEYS, str(e))
