import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

AUTH_TTL_SECONDS = 30 * 60


@dataclass
class AuthState:
    container: str
    mode: str = "phone"
    phone: Optional[str] = None
    phone_code_hash: Optional[str] = None
    client: Optional[Any] = None
    qr_login: Optional[Any] = None
    memory: Optional[Any] = None
    tg_id: Optional[int] = None
    backend: Optional[Any] = None
    created_at: float = field(default_factory=time.time)

    def expired(self) -> bool:
        return (time.time() - self.created_at) > AUTH_TTL_SECONDS


_states: Dict[str, AuthState] = {}


async def disconnect_client(client: Any) -> None:
    try:
        await client.disconnect()
    except Exception:
        pass


def _purge_expired() -> None:
    now = time.time()
    expired = [k for k, v in _states.items() if (now - v.created_at) > AUTH_TTL_SECONDS]
    for key in expired:
        state = _states.pop(key, None)
        if state and state.client:
            asyncio.create_task(disconnect_client(state.client))


def get_state(container: str) -> Optional[AuthState]:
    _purge_expired()
    return _states.get(container)


def clear_state(container: str) -> None:
    state = _states.pop(container, None)
    if state and state.client:
        asyncio.create_task(disconnect_client(state.client))


def set_state(container: str, state: AuthState) -> None:
    _states[container] = state


def take_memory_session(container: str) -> tuple:
    state = get_state(container)
    if not state or not state.memory or not state.tg_id:
        raise ValueError("Not authenticated")
    memory = state.memory
    tg_id = state.tg_id
    clear_state(container)
    return tg_id, memory
