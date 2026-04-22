import time
from dispatchers.utils.serializers import serialize_mongo_document


class TournamentService:

    @staticmethod
    async def create_tournament(db, data, user):

        if user.get("role") != "admin":
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
