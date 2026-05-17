from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from telethon import TelegramClient

from app.setup_web.auth.state import disconnect_client, get_state
from app.setup_web.auth.telethon_client import api_creds


@asynccontextmanager
async def auth_client(container: str) -> AsyncIterator[TelegramClient]:
    """Yield a connected Telethon client for the in-progress setup login."""
    state = get_state(container)
    if not state:
        raise ValueError("Not authenticated")

    if state.client and state.client.is_connected():
        yield state.client
        return

    if not state.memory:
        raise ValueError("Not authenticated")

    api_id, api_hash = await api_creds(container)
    client = TelegramClient(state.memory, api_id, api_hash)
    await client.connect()
    try:
        yield client
    finally:
        await disconnect_client(client)
