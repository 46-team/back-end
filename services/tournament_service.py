import time
from dispatchers.authentication.roles import has_role
from dispatchers.utils.serializers import serialize_mongo_document
from bson import ObjectId

TOURNAMENT_PUBLIC_FIELDS = {
    "_id": 1,
    "title": 1,
    "description": 1,
    "created_by": 1,
    "start_date": 1,
    "end_date": 1,
    "status": 1,
    "created_at": 1,
}

async def get_tournament(db, tournament_id: ObjectId) -> dict | None:
    doc = await db["tournaments"].find_one({"_id": tournament_id}, TOURNAMENT_PUBLIC_FIELDS)
    if not doc:
        return None
    return serialize_mongo_document(doc)

class TournamentService:

    @staticmethod
    async def create_tournament(db, data, user):

        if not has_role(user, "admin"):
            raise Exception("Access denied")

        if "title" not in data:
            raise Exception("Invalid tournament data: 'title' is required")

        tournament = {
            "title": data["title"],
            "description": data.get("description"),
            "created_by": user["_id"],
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
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
