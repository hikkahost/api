from typing import Tuple

from telethon import TelegramClient
from telethon.sessions import MemorySession

from app.setup_web.provision import coerce_api_hash, coerce_api_id, read_config_json


async def api_creds(container: str) -> Tuple[int, str]:
    cfg = await read_config_json(container)
    return coerce_api_id(cfg.get("api_id")), coerce_api_hash(cfg.get("api_hash"))


async def new_client(container: str) -> TelegramClient:
    api_id, api_hash = await api_creds(container)
    client = TelegramClient(MemorySession(), api_id, api_hash)
    await client.connect()
    return client
