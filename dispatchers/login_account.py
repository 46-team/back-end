import uuid
import time
from account import User, UserRole
from register_account import USER_DB, SESSION

class Login_account:
    @staticmethod
    async def login_account(data: dict):
        email = data.get("email")
        password = data.get("password")
        device_token = data.get("device_token")

        if not email or not password or not device_token:
            return {
                "is_ok": False,
                "error_code": "#MISSING_FIELDS",
                "error_message": "All fields are mandatory"
            }

        
        user_record = USER_DB.get(email)

        if not user_record or user_record["password"] != password:
            return {
                "is_ok": False,
                "error_code": "#AUTH_FAILED",
                "error_message": "Wrong password or email"
            }

        user_instance: User = user_record["user"]

        
        SESSION[device_token] = user_instance.id

        return {
            "is_ok": True,
            "type": "login-account",
            "data": {
                "user": {
                    "id": user_instance.id,
                    "name": user_instance.name,
                    "email": user_instance.email,
                    "role": int(user_instance.role)
                },
            }
        }