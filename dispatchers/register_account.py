import uuid
import time
import re
from account import User, UserRole
from main import USER_DB, SESSION


class Register_Account:
    @staticmethod
    def validate_name(name: str) -> bool:
        return 3 <= len(name) <= 13

    @staticmethod
    def validate_password(password: str) -> bool:
        if len(password) < 8:
            return False
        if not re.search(r"[A-Za-z]", password):
            return False
        if not re.search(r"\d", password):
            return False
        return True
    @staticmethod
    async def register_account(data: dict):
        name = data.get("name")
        email = data.get("email")
        password = data.get("password") # do hashing !!!!!!!!!!
        role = data.get("role", 0)
        device_token = data.get("device_token")

        if not email or not password or not name:
            return {
                "is_ok": False, 
                "error_code": "#MISSING_FIELDS", 
                "error_message": "Email or password or name are required"
            }
        
        if not Register_Account.validate_name(name):
            return {
                "is_ok": False,
                "error_code": "#INVALID_NAME",
                "error_message": "Name must be from 3 to 50"
            }

        if not Register_Account.validate_password(password):
            return {
                "is_ok": False,
                "error_code": "#WEAK_PASSWORD",
                "error_message": "Password is too weak or short (min 8)"
            }


        user_id = str(uuid.uuid4())
        
    
        new_user = User(
            id=user_id,
            name=name, 
            email=email,
            role=UserRole(role),
            password = password,
            created_at=int(time.time())
        )

        USER_DB[email] = {"user": new_user, "password": password}

        return {
            "is_ok": True,
            "type": "register-account",
            "data": {
                "user_id": new_user.id,
                "name": new_user.name,
                "email": new_user.email,
                "message": "Account registered successfully"
            }
        }