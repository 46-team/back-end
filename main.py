import os
import signal
from dispatchers.utils.dotenv_dispatcher import env_data
import motor.motor_asyncio
import uvicorn
from websocket import app

db_username = env_data.get("SERVER_DB_USERNAME")
db_password = env_data.get("SERVER_DB_PASSWORD")
db_host = env_data["SERVER_DB_IP"]
db_port = env_data["SERVER_DB_PORT"]

if db_username and db_password:
    mongo_uri = f"mongodb://{db_username}:{db_password}@{db_host}:{db_port}/"
else:
    mongo_uri = f"mongodb://{db_host}:{db_port}/"

client = motor.motor_asyncio.AsyncIOMotorClient(
    mongo_uri
)
db = client[env_data["SERVER_DB_NAME"]]


if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=10, ws_ping_timeout=10)
    finally:
        os.kill(os.getpid(), signal.SIGTERM)
