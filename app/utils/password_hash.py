import re

_BCRYPT_HASH_RE = re.compile(
    r"^\$2[aby]\$(?:0[4-9]|[12][0-9]|3[01])\$[./A-Za-z0-9]{53}$"
)


def validate_password_hash(password_hash: str) -> str:
    password_hash = password_hash.strip()
    if not password_hash:
        raise ValueError("Password hash required")
    if not _BCRYPT_HASH_RE.match(password_hash):
        raise ValueError("Invalid password hash")
    return password_hash
