"""Per-userbot Telethon backends.

Every userbot ships its own Telethon fork and reads/writes sessions and raises
errors with *that* fork. A client built with one fork raises that fork's error
classes, so the login flow has to use the matching library end to end — client
creation, session storage and ``except`` clauses alike. This module maps each
userbot to its fork and loads the pieces the auth flow needs.
"""

import importlib
from dataclasses import dataclass
from functools import lru_cache
from types import ModuleType
from typing import Type

from app.setup_web.userbots import userbot_for_container

#   hikka  -> hikkatl   (hikka-tl-new)
#   heroku -> herokutl  (heroku-tl-new)
#   legacy -> legacytl  (Legacy-TL-New)
#   geektg -> telethon  (Telethon-Mod)
TL_LIBRARIES = {
    "hikka": "hikkatl",
    "heroku": "herokutl",
    "legacy": "legacytl",
    "geektg": "telethon",
}

DEFAULT_TAG = "hikka"


@dataclass(frozen=True)
class TLBackend:
    tag: str
    module_name: str
    client_cls: Type
    memory_session_cls: Type
    sqlite_session_cls: Type
    errors: ModuleType
    resolve_username_request_cls: Type

    def new_memory_client(self, api_id: int, api_hash: str):
        return self.client_cls(self.memory_session_cls(), api_id, api_hash)


@lru_cache(maxsize=None)
def get_backend(tag: str) -> TLBackend:
    module_name = TL_LIBRARIES.get(tag, TL_LIBRARIES[DEFAULT_TAG])
    module = importlib.import_module(module_name)
    sessions = importlib.import_module(f"{module_name}.sessions")
    errors = importlib.import_module(f"{module_name}.errors")
    contacts = importlib.import_module(f"{module_name}.tl.functions.contacts")
    return TLBackend(
        tag=tag,
        module_name=module_name,
        client_cls=module.TelegramClient,
        memory_session_cls=sessions.MemorySession,
        sqlite_session_cls=sessions.SQLiteSession,
        errors=errors,
        resolve_username_request_cls=contacts.ResolveUsernameRequest,
    )


async def backend_for_container(container: str) -> TLBackend:
    userbot = await userbot_for_container(container)
    return get_backend(userbot.tag)
