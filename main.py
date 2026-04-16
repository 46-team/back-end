import os
import signal
from dispatchers.utils.dotenv_dispatcher import env_data
import motor.motor_asyncio
import uvicorn
from websocket import app

client = motor.motor_asyncio.AsyncIOMotorClient(
    f"mongodb://{env_data['SERVER_DB_USERNAME']}:{env_data['SERVER_DB_PASSWORD']}@{env_data['SERVER_DB_IP']}:{env_data['SERVER_DB_PORT']}/"
)
db = client[env_data["SERVER_DB_NAME"]]


if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=10, ws_ping_timeout=10)
    finally:
        os.kill(os.getpid(), signal.SIGTERM)
