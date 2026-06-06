import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import aiofiles.os

from app.setup_web import storage

TGCREDS_FILENAME = "tgcreds.json"
_TGCREDS_FALLBACK = {"api_id": 123456, "api_hash": ""}

_VALID_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")

USERBOT_VARIANTS: Dict[str, Dict[str, str]] = {
    "hikka": {"prefix": "hikka", "inline_module": "hikka.inline"},
    "heroku": {"prefix": "heroku", "inline_module": "heroku.inline"},
    "legacy": {"prefix": "legacy", "inline_module": "legacy.inline"},
    "geektg": {"prefix": "geektg", "inline_module": "geektg.inline"},
}


def _strip_prefix(value: str, prefix: str) -> str:
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _strip_suffix(value: str, suffix: str) -> str:
    if value.endswith(suffix):
        return value[: -len(suffix)]
    return value


def _session_tg_id(filename: str, prefix: str) -> str:
    return _strip_suffix(_strip_prefix(filename, f"{prefix}-"), ".session")


@dataclass
class UserbotInfo:
    tag: str
    prefix: str
    inline_module: str


def userbot_for_prefix(prefix: str) -> UserbotInfo:
    spec = USERBOT_VARIANTS.get(prefix, USERBOT_VARIANTS["hikka"])
    return UserbotInfo(tag=prefix, prefix=prefix, inline_module=spec["inline_module"])


def validate_container_name(name: str) -> None:
    if not isinstance(name, str) or not name:
        raise ValueError("Container name is required")
    if not _VALID_NAME_RE.match(name):
        raise ValueError(
            "Invalid container name. Allowed: letters, numbers, '_', '-', '.'"
        )


def repo_root() -> Path:
    override = os.environ.get("HIKKAHOST_REPO_ROOT", "").strip()
    if override:
        return Path(override)
    cwd = Path(os.getcwd())
    if (cwd / "volumes").is_dir():
        return cwd
    return Path(__file__).resolve().parents[2]


def tgcreds_path() -> Path:
    return repo_root() / TGCREDS_FILENAME


def _load_tgcreds() -> Dict[str, object]:
    try:
        raw = tgcreds_path().read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return dict(_TGCREDS_FALLBACK)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return dict(_TGCREDS_FALLBACK)
    if not isinstance(data, dict):
        return dict(_TGCREDS_FALLBACK)
    return data


def default_api_id() -> int:
    try:
        return int(_load_tgcreds().get("api_id") or _TGCREDS_FALLBACK["api_id"])
    except (TypeError, ValueError):
        return int(_TGCREDS_FALLBACK["api_id"])


def default_api_hash() -> str:
    value = _load_tgcreds().get("api_hash")
    if isinstance(value, str) and value:
        return value
    return str(_TGCREDS_FALLBACK["api_hash"])


def volume_dir(container_name: str) -> Path:
    validate_container_name(container_name)
    root = repo_root() / "volumes" / container_name
    resolved = root.resolve()
    volumes_root = (repo_root() / "volumes").resolve()
    if not str(resolved).startswith(str(volumes_root)):
        raise ValueError("Invalid container path")
    return root


def data_dir(container_name: str) -> Path:
    return volume_dir(container_name) / "data"


async def load_env_file(container_name: str) -> Dict[str, str]:
    env_path = volume_dir(container_name) / ".env"
    if not env_path.exists():
        return {}
    env: Dict[str, str] = {}
    for line in (await storage.read_text(env_path)).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def image_tag_from_image(image: str) -> str:
    if ":" in image:
        return image.rsplit(":", 1)[-1].lower()
    if "/" in image:
        return image.rsplit("/", 1)[-1].lower()
    return image.lower()


def userbot_from_image(image: str) -> UserbotInfo:
    tag = image_tag_from_image(image)
    if tag not in USERBOT_VARIANTS:
        lowered = image.lower()
        if "heroku" in lowered:
            tag = "heroku"
        elif "legacy" in lowered:
            tag = "legacy"
        elif "geektg" in lowered or "friendly" in lowered:
            tag = "geektg"
        else:
            tag = "hikka"
    spec = USERBOT_VARIANTS[tag]
    return UserbotInfo(
        tag=tag, prefix=spec["prefix"], inline_module=spec["inline_module"]
    )


async def userbot_for_container(container_name: str) -> UserbotInfo:
    try:
        env = await load_env_file(container_name)
        image = env.get("IMAGE", "fajox/hikkahost:hikka")
        return userbot_from_image(image)
    except (ValueError, OSError):
        return userbot_from_image("fajox/hikkahost:hikka")


def _normalize_bot_username(value) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lstrip("@").lower()
    return cleaned or None


def _bot_from_config(cfg: dict, userbot: UserbotInfo) -> Optional[str]:
    if not isinstance(cfg, dict):
        return None
    inline = cfg.get(userbot.inline_module)
    if isinstance(inline, dict):
        return _normalize_bot_username(inline.get("custom_bot"))
    for spec in USERBOT_VARIANTS.values():
        block = cfg.get(spec["inline_module"])
        if isinstance(block, dict):
            name = _normalize_bot_username(block.get("custom_bot"))
            if name:
                return name
    return None


async def _read_user_config(data: Path, tg_id: int) -> dict:
    return await storage.read_json(data / f"config-{tg_id}.json")


def _session_prefixes(primary: str) -> List[str]:
    return list(
        dict.fromkeys(
            [primary] + [spec["prefix"] for spec in USERBOT_VARIANTS.values()]
        )
    )


async def _iter_sessions(
    data: Path, prefixes: List[str]
) -> List[Tuple[int, UserbotInfo]]:
    items: List[Tuple[int, UserbotInfo]] = []
    for prefix in prefixes:
        info = userbot_for_prefix(prefix)
        for path in sorted(data.glob(f"{prefix}-*.session")):
            try:
                tg_id = int(_session_tg_id(path.name, prefix))
            except ValueError:
                continue
            items.append((tg_id, info))
    return items


async def collect_bot_usernames(container_name: str) -> Dict[int, str]:
    data = data_dir(container_name)
    if not data.exists():
        return {}
    mapping: Dict[int, str] = {}
    prefixes = [spec["prefix"] for spec in USERBOT_VARIANTS.values()]
    for tg_id, userbot in await _iter_sessions(data, prefixes):
        bot = _bot_from_config(await _read_user_config(data, tg_id), userbot)
        if bot:
            mapping[tg_id] = bot
    return mapping


async def list_accounts(container_name: str, userbot: UserbotInfo) -> List[Dict]:
    data = data_dir(container_name)
    if not data.exists():
        return []
    accounts: List[Dict] = []
    seen: Set[int] = set()
    for tg_id, info in await _iter_sessions(data, _session_prefixes(userbot.prefix)):
        if tg_id in seen:
            continue
        seen.add(tg_id)
        accounts.append(
            {
                "tg_id": tg_id,
                "bot_username": _bot_from_config(
                    await _read_user_config(data, tg_id), info
                ),
            }
        )
    accounts.sort(key=lambda item: item["tg_id"])
    return accounts


async def delete_account(container_name: str, tg_id: int) -> None:
    if not isinstance(tg_id, int) or tg_id <= 0:
        raise ValueError("Invalid tg_id")
    data = data_dir(container_name)
    if not data.exists():
        raise ValueError("account_not_found")
    removed = False
    prefixes = {spec["prefix"] for spec in USERBOT_VARIANTS.values()}
    for prefix in prefixes:
        for name in (f"{prefix}-{tg_id}.session", f"{prefix}-{tg_id}.session-journal"):
            if await storage.unlink_if_exists(data / name):
                removed = True
    if await storage.unlink_if_exists(data / f"config-{tg_id}.json"):
        removed = True
    if not removed:
        raise ValueError("account_not_found")
