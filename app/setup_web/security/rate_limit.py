import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from sanic import Request
from sanic.response import HTTPResponse, json

from app.setup_web.security.container import resolve_container
from app.setup_web.security.proxy import client_ip, strip_untrusted_proxy_headers

_rate_buckets: Dict[str, List[float]] = defaultdict(list)

RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "/setup/phone/send": (3, 300),
    "/setup/phone/verify": (10, 60),
    "/setup/qr/init": (10, 60),
    "/setup/qr/poll": (30, 60),
    "/setup/qr/2fa": (10, 60),
    "/setup/finish": (5, 3600),
    "/setup/bot/check": (20, 60),
    "/setup/credentials": (20, 60),
    "/setup/auth/mode": (20, 60),
    "/setup/accounts": (60, 60),
    "/setup/csrf": (30, 60),
}

GLOBAL_LIMIT = (120, 60)


def _check_rate(key: str, limit: int, window: int) -> bool:
    now = time.time()
    bucket = _rate_buckets[key]
    _rate_buckets[key] = [t for t in bucket if now - t < window]
    if len(_rate_buckets[key]) >= limit:
        return False
    _rate_buckets[key].append(now)
    return True


def rate_limit_middleware(request: Request) -> Optional[HTTPResponse]:
    strip_untrusted_proxy_headers(request)
    ip = client_ip(request)
    path = request.path
    global_key = f"global:{ip}"
    if not _check_rate(global_key, GLOBAL_LIMIT[0], GLOBAL_LIMIT[1]):
        return json({"error": "Too many requests"}, status=429)
    for prefix, (limit, window) in RATE_LIMITS.items():
        if path.startswith(prefix) or path == prefix:
            key = f"{prefix}:{ip}"
            if not _check_rate(key, limit, window):
                return json({"error": "Too many requests"}, status=429)
            if path == "/setup/finish":
                try:
                    container = resolve_container(request)
                    ckey = f"finish:{container}"
                    if not _check_rate(ckey, limit, window):
                        return json({"error": "Too many requests"}, status=429)
                except PermissionError:
                    pass
            break
    return None
