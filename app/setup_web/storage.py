import json
import os
from pathlib import Path
from typing import Any, Dict
import aiofiles
import aiofiles.os


async def read_text(path: Path) -> str:
    async with aiofiles.open(path, "r", encoding="utf-8") as handle:
        return await handle.read()


async def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(await read_text(path))
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


async def atomic_write(path: Path, content: str, mode: int = 0o644) -> None:
    await aiofiles.os.makedirs(path.parent, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    async with aiofiles.open(tmp, "w", encoding="utf-8") as handle:
        await handle.write(content)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


async def write_json(path: Path, data: Dict[str, Any]) -> None:
    await atomic_write(path, json.dumps(data, indent=4) + "\n")
    await chmod_secrets(path)


async def chmod_secrets(path: Path) -> None:
    if path.exists():
        os.chmod(path, 0o600)
    if path.parent.exists():
        os.chmod(path.parent, 0o700)


async def unlink_if_exists(path: Path) -> bool:
    if not path.is_file():
        return False
    await aiofiles.os.remove(path)
    return True
