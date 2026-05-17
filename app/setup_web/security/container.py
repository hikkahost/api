import hmac
import os
import re
from typing import Optional

from sanic import Request

from app.config import SERVER
from app.setup_web.security.proxy import HIKKAHOST_CONTAINER_HEADER, is_trusted_proxy
from app.setup_web.userbots import validate_container_name


def parse_container_from_host(host: str) -> Optional[str]:
    if not host:
        return None
    host = host.split(":")[0]
    pattern = re.compile(
        rf"^([A-Za-z0-9][A-Za-z0-9_.-]{{0,62}})\.{re.escape(SERVER)}\.hikka\.host$"
    )
    match = pattern.match(host)
    if match:
        return match.group(1)
    return None


def resolve_container(request: Request) -> str:
    """
    Container identity comes only from the Host subdomain (or dev override).
    X-Hikkahost-Container is an optional cross-check from Caddy, never a fallback.
    """
    dev_container = os.environ.get("SETUP_WEB_DEV_CONTAINER", "").strip()
    host = (request.headers.get("Host") or "").split(":")[0]
    allow_dev = os.environ.get("SETUP_WEB_ALLOW_DEV", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if dev_container and host in ("127.0.0.1", "localhost") and allow_dev:
        validate_container_name(dev_container)
        return dev_container

    host_container = parse_container_from_host(request.headers.get("Host", ""))
    if not host_container:
        raise PermissionError("Unknown container")

    if is_trusted_proxy(request):
        header_container = (
            request.headers.get(HIKKAHOST_CONTAINER_HEADER) or ""
        ).strip()
        if header_container and not hmac.compare_digest(
            header_container, host_container
        ):
            raise PermissionError("Container header mismatch")

    validate_container_name(host_container)
    return host_container
