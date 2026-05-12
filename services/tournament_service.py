import time
import logging
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from dispatchers.authentication.roles import has_role
from dispatchers.utils.serializers import serialize_mongo_document, serialize_public_user

logger = logging.getLogger(__name__)
ALLOWED_STATUSES = {"Draft", "Registration", "Running", "Finished"}
TOURNAMENT_PUBLIC_FIELDS = {
    "_id": 1,
    "title": 1,
    "description": 1,
    "created_by": 1,
    "start_date": 1,
    "end_date": 1,
    "status": 1,
    "created_at": 1,
    "updated_at": 1,
}
TOURNAMENT_DETAIL_FIELDS = {
    **TOURNAMENT_PUBLIC_FIELDS,
    "participant_ids": 1,
}
async def change_tournament_status(db, tournament_id: ObjectId, status: str, user=None) -> dict | None:
    if user is None:
        raise Exception("Access denied")

    return await TournamentService.change_tournament_status(db, tournament_id, status, user)


ACTUAL_TOURNAMENT_FILTER = {"status": {"$ne": "Archived"}}


def _validate_tournament_dates(start_date, end_date):
    if start_date is None or end_date is None:
        return

    try:
        parsed_start = datetime.fromisoformat(start_date)
        parsed_end = datetime.fromisoformat(end_date)
    except (TypeError, ValueError):
        raise Exception("Invalid tournament dates")

    if parsed_start >= parsed_end:
        raise Exception("Invalid tournament dates: 'start_date' must be earlier than 'end_date'")


async def get_tournament(db, tournament_id: ObjectId) -> dict | None:
    doc = await db["tournaments"].find_one({"_id": tournament_id}, TOURNAMENT_DETAIL_FIELDS)
    if not doc:
        return None

    participant_ids = doc.pop("participant_ids", []) or []
    participants = []
    for participant_id in participant_ids:
        participant = await db["users"].find_one({"_id": participant_id})
        if participant:
            participants.append(serialize_public_user(participant))

    tournament = serialize_mongo_document(doc)
    tournament["participants"] = participants
    return tournament

class TournamentService:

    @staticmethod
    async def create_tournament(db, data, user):

        if not has_role(user, "organizer"):
            raise Exception("Access denied")

        if "title" not in data:
            raise Exception("Invalid tournament data: 'title' is required")

        _validate_tournament_dates(data.get("start_date"), data.get("end_date"))

        tournament = {
            "title": data["title"],
            "description": data.get("description"),
            "created_by": user["_id"],
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "participant_ids": [],
            "status": "Draft",
            "created_at": int(time.time())
        }

        result = await db["tournaments"].insert_one(tournament)

        tournament["_id"] = str(result.inserted_id)
        return serialize_mongo_document(tournament)
    
    @staticmethod
    async def get_tournaments(db):
        tournaments_cursor = db["tournaments"].find({})

        tournaments = []
        async for tournament in tournaments_cursor:
            tournaments.append(serialize_mongo_document(tournament))

        return tournaments

    @staticmethod
    async def get_actual_tournaments(db, user):
        if not user:
            raise Exception("Authentication required")

        if has_role(user, "admin"):
            query = ACTUAL_TOURNAMENT_FILTER
        elif has_role(user, "organizer"):
            query = {
                "$and": [
                    ACTUAL_TOURNAMENT_FILTER,
                    {"created_by": user["_id"]},
                ]
            }
        else:
            query = {
                "$and": [
                    ACTUAL_TOURNAMENT_FILTER,
                    {"participant_ids": user["_id"]},
                ]
            }

        tournaments_cursor = db["tournaments"].find(query, TOURNAMENT_PUBLIC_FIELDS)

        tournaments = []
        async for tournament in tournaments_cursor:
            tournaments.append(serialize_mongo_document(tournament))

        return tournaments

    @staticmethod
    async def assign_participants(db, tournament_id, participant_ids, user):
        if not has_role(user, "organizer"):
            raise Exception("Access denied")

        if not tournament_id or participant_ids is None:
            raise Exception("Required data is missing")

        try:
            tournament_object_id = ObjectId(tournament_id)
        except (InvalidId, TypeError):
            raise Exception("Invalid tournament_id")

        if not isinstance(participant_ids, list):
            raise Exception("Invalid participant_ids")

        tournament = await db["tournaments"].find_one({"_id": tournament_object_id})
        if not tournament:
            raise Exception("Tournament not found")

        if tournament.get("created_by") != user["_id"]:
            raise Exception("Access denied")

        participant_object_ids = []
        for user_id in participant_ids:
            try:
                participant_object_ids.append(ObjectId(user_id))
            except (InvalidId, TypeError):
                raise Exception("Invalid user_id")

        for participant_object_id in participant_object_ids:
            participant = await db["users"].find_one({"_id": participant_object_id})
            if not participant:
                raise Exception("User not found")

        await db["tournaments"].update_one(
            {"_id": tournament_object_id},
            {"$set": {"participant_ids": participant_object_ids}}
        )

        tournament["participant_ids"] = participant_object_ids
        return serialize_mongo_document(tournament)

    @staticmethod
    async def update_tournament(db, tournament_id, data, user):
        if not has_role(user, "organizer"):
            raise Exception("Access denied")

        if not tournament_id:
            raise Exception("Required data is missing")

        try:
            tournament_object_id = ObjectId(tournament_id)
        except (InvalidId, TypeError):
            raise Exception("Invalid tournament_id")

        tournament = await db["tournaments"].find_one({"_id": tournament_object_id})
        if not tournament:
            raise Exception("Tournament not found")

        if tournament.get("created_by") != user["_id"]:
            raise Exception("Access denied")

        updates = {}
        editable_fields = ("title", "description", "start_date", "end_date")
        for field in editable_fields:
            if field in data:
                updates[field] = data[field]

        if "title" in updates and (
            updates["title"] is None or not str(updates["title"]).strip()
        ):
            raise Exception("Invalid tournament data: 'title' cannot be empty")

        start_date = updates.get("start_date", tournament.get("start_date"))
        end_date = updates.get("end_date", tournament.get("end_date"))
        _validate_tournament_dates(start_date, end_date)

        updates["updated_at"] = int(time.time())

        await db["tournaments"].update_one(
            {"_id": tournament_object_id},
            {"$set": updates}
        )

        tournament.update(updates)
        return serialize_mongo_document(tournament)

    @staticmethod
    async def change_tournament_status(db, tournament_id, status, user):
        if not has_role(user, "organizer"):
            raise Exception("Access denied")

        if not tournament_id or not status:
            raise Exception("Required data is missing")

        if status not in ALLOWED_STATUSES:
            raise Exception(f"Invalid status. Allowed values: {', '.join(sorted(ALLOWED_STATUSES))}.")

        try:
            tournament_object_id = ObjectId(tournament_id)
        except (InvalidId, TypeError):
            raise Exception("Invalid tournament_id")

        tournament = await db["tournaments"].find_one({"_id": tournament_object_id})
        if not tournament:
            raise Exception("Tournament not found")

        if tournament.get("created_by") != user["_id"]:
            raise Exception("Access denied")

        updated_at = int(time.time())
        await db["tournaments"].update_one(
            {"_id": tournament_object_id},
            {"$set": {"status": status, "updated_at": updated_at}}
        )

        return await get_tournament(db, tournament_object_id)

    @staticmethod
    async def upsert_submission(db, data, user, email_sender=None):
        if not has_role(user, "team"):
            raise Exception("Access denied")

        required_fields = ("tournament_id", "repository_url", "video_demo_url")
        if any(not data.get(field) for field in required_fields):
            raise Exception("Required data is missing")

        try:
            tournament_object_id = ObjectId(data.get("tournament_id"))
        except (InvalidId, TypeError):
            raise Exception("Invalid tournament_id")

        tournament = await db["tournaments"].find_one({"_id": tournament_object_id})
        if not tournament:
            raise Exception("Tournament not found")

        team_id = user.get("_id")
        if team_id not in (tournament.get("participant_ids") or []):
            raise Exception("Access denied")

        now = int(time.time())
        submissions = db["tournament_submissions"]
        existing_submission = await submissions.find_one(
            {
                "tournament_id": tournament_object_id,
                "team_id": team_id,
            }
        )

        updates = {
            "repository_url": data["repository_url"],
            "video_demo_url": data["video_demo_url"],
            "live_demo_url": data.get("live_demo_url"),
            "description": data.get("description"),
            "updated_at": now,
            "submitted_at": now,
        }

        if existing_submission:
            await submissions.update_one(
                {"_id": existing_submission["_id"]},
                {"$set": updates},
            )
            existing_submission.update(updates)
            submission = existing_submission
        else:
            submission = {
                "tournament_id": tournament_object_id,
                "team_id": team_id,
                **updates,
                "created_at": now,
            }
            result = await submissions.insert_one(submission)
            submission["_id"] = result.inserted_id

        email_sent = False
        if email_sender:
            try:
                organizer = await db["users"].find_one({"_id": tournament.get("created_by")})
                await email_sender(
                    tournament=tournament,
                    organizer=organizer,
                    team=user,
                    submission=submission,
                )
                email_sent = True
            except Exception:
                logger.exception("Failed to send tournament submission notification")

        return {
            "submission": serialize_mongo_document(submission),
            "email_sent": email_sent,
        }
