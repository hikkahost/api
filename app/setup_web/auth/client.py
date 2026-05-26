from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Tuple

from app.setup_web.auth.state import disconnect_client, get_state
from app.setup_web.provision import (
    coerce_api_hash,
    coerce_api_id,
    read_config_json,
)
from app.setup_web.tl import TLBackend, backend_for_container


async def api_creds(container: str) -> Tuple[int, str]:
    cfg = await read_config_json(container)
    return coerce_api_id(cfg.get("api_id")), coerce_api_hash(cfg.get("api_hash"))


async def new_client(container: str) -> Tuple[TLBackend, Any]:
    """Connect a fresh client using the fork that matches this container's userbot."""
    backend = await backend_for_container(container)
    api_id, api_hash = await api_creds(container)
    client = backend.new_memory_client(api_id, api_hash)
    await client.connect()
    return backend, client


@asynccontextmanager
async def auth_client(container: str) -> AsyncIterator[Any]:
    """Yield a connected client for the in-progress setup login."""
    state = get_state(container)
    if not state:
        raise ValueError("Not authenticated")

    if state.client and state.client.is_connected():
        yield state.client
        return

    if not state.memory:
        raise ValueError("Not authenticated")

    backend = state.backend or await backend_for_container(container)
    api_id, api_hash = await api_creds(container)
    client = backend.client_cls(state.memory, api_id, api_hash)
    await client.connect()
    try:
        yield client
    finally:
        await disconnect_client(client)
