import asyncio
from typing import Dict

from app.setup_web.auth.client import new_client
from app.setup_web.auth.helpers import finalize_login, map_sign_in_error, require_state
from app.setup_web.auth.state import AuthState, clear_state, get_state, set_state
from app.setup_web.utils.qr_render import render_qr_data_uri


async def qr_init(container: str) -> Dict:
    clear_state(container)
    backend, client = await new_client(container)
    state = AuthState(container=container, mode="qr", client=client, backend=backend)
    qr_login = await client.qr_login()
    state.qr_login = qr_login
    set_state(container, state)

    rendered = await render_qr_data_uri(qr_login.url)
    return {"qr_url": qr_login.url, **rendered}


async def qr_poll(container: str) -> Dict:
    state = require_state(get_state(container), mode="qr", need_qr=True)
    try:
        await state.qr_login.wait(timeout=1)
    except asyncio.TimeoutError:
        return {"status": "pending"}
    except state.backend.errors.SessionPasswordNeededError:
        return {"status": "needs_2fa"}
    except Exception:
        return {"status": "pending"}

    return {"status": "authorized", **await finalize_login(state)}


async def qr_2fa(container: str, password: str) -> Dict:
    state = require_state(get_state(container), mode="qr")
    try:
        await state.client.sign_in(password=password)
    except Exception as exc:
        raise map_sign_in_error(state.backend, exc) from exc
    return await finalize_login(state)
