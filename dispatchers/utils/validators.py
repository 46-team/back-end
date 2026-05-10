import re


EMAIL_FORMAT_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def is_valid_email_format(email: str) -> bool:
    return bool(EMAIL_FORMAT_RE.fullmatch(email))
