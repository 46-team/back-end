import hashlib
import uuid


def generate_device_token() -> str:
    return hashlib.sha256(uuid.uuid4().hex.encode("utf-8")).hexdigest()
