ALLOWED_ROLES = ("admin", "team", "jury", "organizer")
DEFAULT_ROLE = "team"


def normalize_role(role):
    if not isinstance(role, str):
        return None

    normalized_role = role.strip().lower()
    return normalized_role or None


def is_allowed_role(role):
    normalized_role = normalize_role(role)
    return normalized_role in ALLOWED_ROLES


def has_role(user, role):
    if not isinstance(user, dict):
        return False

    return normalize_role(user.get("role")) == normalize_role(role)


def normalize_user_role(user):
    if not isinstance(user, dict):
        return None

    normalized_role = normalize_role(user.get("role"))
    if normalized_role:
        user["role"] = normalized_role

    return normalized_role
