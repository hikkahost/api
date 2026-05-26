from typing import Dict, Literal, Optional

from app.setup_web.auth.state import AuthState, clear_state
from app.setup_web.tl import TLBackend
from app.setup_web.utils.telegram_profile import user_profile

AuthMode = Literal["phone", "qr"]
AUTH_MODES = frozenset({"phone", "qr"})


def ensure_auth_mode(mode: str) -> None:
    if mode not in AUTH_MODES:
        raise ValueError("Invalid auth mode")


def require_state(
    state: Optional[AuthState],
    *,
    mode: AuthMode,
    need_client: bool = True,
    need_qr: bool = False,
) -> AuthState:
    if not state or state.mode != mode:
        raise ValueError(f"No active {mode} login")
    if need_client and not state.client:
        raise ValueError(f"No active {mode} login")
    if need_qr and not state.qr_login:
        raise ValueError("No active QR login")
    if state.expired():
        clear_state(state.container)
        raise ValueError("Session expired")
    return state


async def finalize_login(state: AuthState) -> Dict:
    me = await state.client.get_me()
    state.memory = state.client.session
    state.tg_id = me.id
    return user_profile(me)


def map_sign_in_error(backend: TLBackend, exc: Exception) -> ValueError:
    errors = backend.errors
    if isinstance(exc, errors.PhoneCodeInvalidError):
        return ValueError("Invalid code")
    if isinstance(exc, errors.PasswordHashInvalidError):
        return ValueError("Invalid 2FA password")
    if isinstance(exc, errors.FloodWaitError):
        return ValueError(f"Flood wait: try again in {exc.seconds}s")
    raise exc
