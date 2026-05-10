MESSAGE_TYPE = "upsert_tournament_submission"


async def send_upsert_submission_error(client, proto, ENCRYPTION_KEYS, error):
    await proto.send_message(
        {
            "is_ok": False,
            "type": MESSAGE_TYPE,
            "error": error,
        },
        ENCRYPTION_KEYS[client]["key"],
    )


async def upsert_tournament_submission_handler(client, message, db, USER_TOKENS, proto, ENCRYPTION_KEYS):
    token = message.get("device_token")

    if not token or token not in USER_TOKENS:
        await send_upsert_submission_error(client, proto, ENCRYPTION_KEYS, "Authentication required")
        return

    session = USER_TOKENS[token]
    user = session[1]

    from services.email_service import send_tournament_submission_notification
    from services.tournament_service import TournamentService

    try:
        result = await TournamentService.upsert_submission(
            db=db,
            data=message,
            user=user,
            email_sender=send_tournament_submission_notification,
        )

        await proto.send_message(
            {
                "is_ok": True,
                "type": MESSAGE_TYPE,
                "submission": result["submission"],
                "email_sent": result["email_sent"],
            },
            ENCRYPTION_KEYS[client]["key"],
        )

    except Exception as e:
        await send_upsert_submission_error(client, proto, ENCRYPTION_KEYS, str(e))
