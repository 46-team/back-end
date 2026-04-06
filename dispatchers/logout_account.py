from main import SESSION

class LogoutAccount:
    @staticmethod
    async def logout_account(data: dict):
        device_token = data.get("device_token")

        if not device_token:
            return {
            "is_ok": False,
            "type": "account-logout",
            "error_code": "#MISSING_TOKEN",
            "error_message": "Field device_token is missing"
            }
        removed_user_id = SESSION(device_token, None)

        if removed_user_id:
            return{
                "is_ok": True,
                "type": "account-logout",
                "data":{
                    "message": "Session success end",
                    "device_token": device_token
                }
            }
        else:
            return{
                "is_ok": False,
                "type": "account-logout",
                "error_code": "#SESSION_NOT_FOUND",
                "error_message": "No active session found for this token"
            }