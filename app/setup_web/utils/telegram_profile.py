from html import escape
from typing import Dict


def user_profile(me) -> Dict:
    """Build display fields for the setup UI; names are HTML-escaped."""
    username = (getattr(me, "username", None) or "").strip()
    first = (getattr(me, "first_name", None) or "").strip()
    last = (getattr(me, "last_name", None) or "").strip()
    if last:
        first = f"{first} {last}".strip()
    safe_name = escape(first) if first else ""
    safe_user = escape(username) if username else ""
    if first and username:
        label = f"{safe_name} (@{safe_user})"
    elif first:
        label = safe_name
    elif username:
        label = f"@{safe_user}"
    else:
        label = str(me.id)
    return {
        "tg_id": me.id,
        "username": safe_user,
        "first_name": safe_name,
        "display_name": label,
    }
