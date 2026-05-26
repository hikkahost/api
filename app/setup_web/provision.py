import logging
import math
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

import aiofiles.os

from app.setup_web import storage
from app.setup_web.tl import TLBackend, get_backend
from app.setup_web.docker_ops import (
    container_is_running,
    restart_container,
    start_container,
    stop_container,
)
from app.setup_web.userbots import (
    DEFAULT_API_HASH,
    DEFAULT_API_ID,
    UserbotInfo,
    data_dir,
    userbot_for_container,
)

logger = logging.getLogger("setup_web")

_APP_NAME_WORDS = (
    "Cresco",
    "Cibus",
    "Consilium",
    "Lumen",
    "Vox",
    "Nexus",
    "Astra",
    "Vita",
    "Aura",
    "Nova",
)


def provision_lock_path(container_name: str) -> Path:
    return data_dir(container_name).parent / ".provision.lock"


async def acquire_provision_lock(container_name: str) -> bool:
    lock = provision_lock_path(container_name)
    await aiofiles.os.makedirs(lock.parent, exist_ok=True)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, b"1")
        os.close(fd)
        os.chmod(lock, 0o600)
        return True
    except FileExistsError:
        return False


async def release_provision_lock(container_name: str) -> None:
    lock = provision_lock_path(container_name)
    try:
        await aiofiles.os.remove(lock)
    except FileNotFoundError:
        pass
    except OSError:
        pass


@asynccontextmanager
async def provision_lock(container_name: str) -> AsyncIterator[None]:
    if not await acquire_provision_lock(container_name):
        raise RuntimeError("Provision already in progress")
    try:
        yield
    finally:
        await release_provision_lock(container_name)


async def read_config_json(container_name: str) -> Dict[str, Any]:
    return await storage.read_json(data_dir(container_name) / "config.json")


def coerce_api_id(value: Any) -> int:
    if value is None or value == "":
        return DEFAULT_API_ID
    try:
        if isinstance(value, float) and not math.isfinite(value):
            return DEFAULT_API_ID
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_API_ID


def coerce_api_hash(value: Any) -> str:
    if not value:
        return DEFAULT_API_HASH
    return str(value)


def generate_app_name() -> str:
    return " ".join(secrets.choice(_APP_NAME_WORDS) for _ in range(3))


def validate_api_hash(api_hash: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{32}", api_hash.lower())) if api_hash else False


async def merge_credentials(
    container_name: str,
    api_id: int,
    api_hash: str,
    app_name: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = await read_config_json(container_name)
    cfg["api_id"] = api_id
    cfg["api_hash"] = api_hash
    if app_name:
        cfg["app_name"] = app_name
    elif not cfg.get("app_name"):
        cfg["app_name"] = generate_app_name()
    await storage.write_json(data_dir(container_name) / "config.json", cfg)
    return cfg


async def apply_credentials(
    container_name: str,
    api_id: int,
    api_hash: str,
    app_name: Optional[str] = None,
) -> Dict[str, Any]:
    async with provision_lock(container_name):
        was_running = await container_is_running(container_name)
        try:
            if was_running:
                await stop_container(container_name)
            cfg = await merge_credentials(container_name, api_id, api_hash, app_name)
            if was_running:
                await start_container(container_name)
        except Exception as exc:
            logger.exception("apply_credentials container=%s failed", container_name)
            raise RuntimeError("credentials_apply_failed") from exc
        return cfg


async def save_session_file(
    container_name: str,
    userbot: UserbotInfo,
    tg_id: int,
    memory: Any,
    backend: TLBackend,
) -> Path:
    data = data_dir(container_name)
    await aiofiles.os.makedirs(data, exist_ok=True)
    session_path = data / f"{userbot.prefix}-{tg_id}"
    sqlite = backend.sqlite_session_cls(str(session_path))
    sqlite.set_dc(memory.dc_id, memory.server_address, memory.port)
    sqlite.auth_key = memory.auth_key
    sqlite.save()
    file_path = Path(f"{session_path}.session")
    await storage.chmod_secrets(file_path)
    return file_path


async def merge_user_config(
    container_name: str,
    userbot: UserbotInfo,
    tg_id: int,
    bot_username: str,
) -> None:
    path = data_dir(container_name) / f"config-{tg_id}.json"
    cfg = await storage.read_json(path)
    inline_key = userbot.inline_module
    inline = cfg.get(inline_key, {})
    if not isinstance(inline, dict):
        inline = {}
    inline["custom_bot"] = bot_username.lstrip("@").lower()
    cfg[inline_key] = inline
    await storage.write_json(path, cfg)


async def finish_provision(
    container_name: str,
    tg_id: int,
    memory_session: Any,
    bot_username: str,
) -> None:
    async with provision_lock(container_name):
        userbot = await userbot_for_container(container_name)
        backend = get_backend(userbot.tag)
        cfg = await read_config_json(container_name)
        if not cfg.get("api_id") or not cfg.get("api_hash"):
            await merge_credentials(container_name, DEFAULT_API_ID, DEFAULT_API_HASH)
        await save_session_file(container_name, userbot, tg_id, memory_session, backend)
        await merge_user_config(container_name, userbot, tg_id, bot_username)
        try:
            await restart_container(container_name)
        except Exception as exc:
            logger.exception(
                "finish_provision restart container=%s failed", container_name
            )
            raise RuntimeError("provision_failed") from exc
