import os
from dotenv import dotenv_values

env_data = dict(os.environ)
local_env = dotenv_values("config/.env")
env_data.update({k: v for k, v in local_env.items() if v is not None})
