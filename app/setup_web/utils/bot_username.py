import re
import secrets
import string
from typing import Any, Dict, Optional

from app.setup_web.auth.client import auth_client
from app.setup_web.tl import backend_for_container
from app.setup_web.userbots import collect_bot_usernames


def suggest_bot_username(prefix: str = "hikka") -> str:
    safe = re.sub(r"[^a-z0-9]", "", (prefix or "hikka").lower()) or "hikka"
    alphabet = string.ascii_lowercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"{safe}_{suffix}_bot"


_USERNAME_CHARS_RE = re.compile(r"^[a-z0-9_]+$")


def _validate_format(username: str) -> str:
    username = username.lstrip("@").lower()
    if not username:
        raise ValueError("Bot username required")
    if not _USERNAME_CHARS_RE.match(username):
        raise ValueError("bot_username_invalid_chars")
    if len(username) < 3 or len(username) > 32:
        raise ValueError("Invalid bot username format")
    if not username.endswith("bot"):
        raise ValueError("Bot username must end with 'bot'")
    return username


async def _check_local_collision(
    container: str, username: str, tg_id: Optional[int]
) -> None:
    used = await collect_bot_usernames(container)
    for acc_id, existing in used.items():
        if existing == username and acc_id != tg_id:
            raise ValueError("bot_username_taken")


async def _is_username_taken_on_telegram(
    backend: Any, client: Any, username: str
) -> bool:
    try:
        await client(backend.resolve_username_request_cls(username=username))
        return True
    except backend.errors.UsernameNotOccupiedError:
        return False


async def _check_telegram_available(container: str, username: str) -> None:
    backend = await backend_for_container(container)
    async with auth_client(container) as client:
        if await _is_username_taken_on_telegram(backend, client, username):
            raise ValueError("bot_username_taken")


async def validate_bot_username(
    container: str,
    bot_username: str,
    tg_id: Optional[int] = None,
) -> str:
    username = _validate_format(bot_username)
    await _check_local_collision(container, username, tg_id)
    await _check_telegram_available(container, username)
    return username


async def check_bot_username(
    container: str,
    bot_username: str,
    tg_id: Optional[int] = None,
) -> Dict:
    username = await validate_bot_username(container, bot_username, tg_id=tg_id)
    return {"username": username, "ok": True, "available": True}
