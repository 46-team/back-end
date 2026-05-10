import asyncio
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone

from dispatchers.utils.dotenv_dispatcher import env_data


def _smtp_port():
    try:
        return int(env_data.get("SMTP_PORT", 587))
    except (TypeError, ValueError):
        return 587


def _smtp_uses_tls():
    return str(env_data.get("SMTP_USE_TLS", "true")).strip().lower() in {"1", "true", "yes"}


def _format_submission_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _build_submission_email(tournament, organizer, team, submission):
    recipient = (organizer or {}).get("email")
    if not recipient:
        raise Exception("Tournament organizer email is missing")

    from_email = env_data.get("SMTP_FROM_EMAIL") or env_data.get("SMTP_USERNAME")
    if not from_email:
        raise Exception("SMTP_FROM_EMAIL is required")

    tournament_title = tournament.get("title", "Tournament")
    team_name = team.get("full_name") or team.get("login") or str(team.get("_id"))
    team_email = team.get("email") or ""
    submitted_at = _format_submission_timestamp(submission["submitted_at"])

    lines = [
        f"Tournament: {tournament_title}",
        f"Team: {team_name}",
        f"Team email: {team_email}",
        f"Repository: {submission['repository_url']}",
        f"Demo video: {submission['video_demo_url']}",
    ]

    if submission.get("live_demo_url"):
        lines.append(f"Live demo: {submission['live_demo_url']}")

    if submission.get("description"):
        lines.append("")
        lines.append("Description:")
        lines.append(str(submission["description"]))

    lines.extend(["", f"Submitted at: {submitted_at}"])

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = recipient
    message["Subject"] = f"New submission for {tournament_title}"
    message.set_content("\n".join(lines))
    return message


def _send_email_sync(message):
    host = env_data.get("SMTP_HOST")
    if not host:
        raise Exception("SMTP_HOST is required")

    username = env_data.get("SMTP_USERNAME")
    password = env_data.get("SMTP_PASSWORD")

    with smtplib.SMTP(host, _smtp_port()) as smtp:
        if _smtp_uses_tls():
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


async def send_tournament_submission_notification(tournament, organizer, team, submission):
    message = _build_submission_email(
        tournament=tournament,
        organizer=organizer,
        team=team,
        submission=submission,
    )
    await asyncio.to_thread(_send_email_sync, message)
