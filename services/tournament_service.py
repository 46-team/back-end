import time
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from dispatchers.authentication.roles import has_role
from dispatchers.utils.serializers import serialize_mongo_document

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

async def get_tournament(db, tournament_id: ObjectId) -> dict | None:
    doc = await db["tournaments"].find_one({"_id": tournament_id}, TOURNAMENT_PUBLIC_FIELDS)
    if not doc:
        return None
    return serialize_mongo_document(doc)

class TournamentService:

    @staticmethod
    async def create_tournament(db, data, user):

        if not has_role(user, "organizer"):
            raise Exception("Access denied")

        if "title" not in data:
            raise Exception("Invalid tournament data: 'title' is required")

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
        if start_date is not None and end_date is not None:
            try:
                parsed_start = datetime.fromisoformat(start_date)
                parsed_end = datetime.fromisoformat(end_date)
            except (TypeError, ValueError):
                raise Exception("Invalid tournament dates")

            if parsed_start >= parsed_end:
                raise Exception("Invalid tournament dates: 'start_date' must be earlier than 'end_date'")

        updates["updated_at"] = int(time.time())

        await db["tournaments"].update_one(
            {"_id": tournament_object_id},
            {"$set": updates}
        )

        tournament.update(updates)
        return serialize_mongo_document(tournament)
