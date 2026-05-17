from typing import Dict, Optional

from telethon.errors import (
    FloodWaitError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)

from app.setup_web.auth.helpers import (
    ensure_auth_mode,
    finalize_login,
    map_sign_in_error,
    require_state,
)
from app.setup_web.auth.state import (
    AuthState,
    clear_state,
    disconnect_client,
    get_state,
    set_state,
)
from app.setup_web.auth.telethon_client import new_client


async def set_auth_mode(container: str, mode: str) -> None:
    ensure_auth_mode(mode)
    clear_state(container)
    set_state(container, AuthState(container=container, mode=mode))


async def phone_send(container: str, phone: str) -> Dict:
    clear_state(container)
    state = AuthState(container=container, mode="phone", phone=phone)
    client = await new_client(container)
    state.client = client
    try:
        sent = await client.send_code_request(phone)
        state.phone_code_hash = sent.phone_code_hash
        set_state(container, state)
        return {"ok": True}
    except PhoneNumberInvalidError:
        await disconnect_client(client)
        raise ValueError("Invalid phone number")
    except FloodWaitError as exc:
        await disconnect_client(client)
        raise ValueError(f"Flood wait: try again in {exc.seconds}s")


async def phone_verify(
    container: str, code: str, password: Optional[str] = None
) -> Dict:
    state = require_state(get_state(container), mode="phone")
    try:
        await state.client.sign_in(
            phone=state.phone,
            code=code,
            phone_code_hash=state.phone_code_hash,
        )
    except SessionPasswordNeededError:
        if not password:
            return {"needs_2fa": True}
        try:
            await state.client.sign_in(password=password)
        except Exception as exc:
            raise map_sign_in_error(exc) from exc
    except Exception as exc:
        raise map_sign_in_error(exc) from exc

    return await finalize_login(state)
