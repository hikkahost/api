import ipaddress

from sanic import Request

HIKKAHOST_CONTAINER_HEADER = "X-Hikkahost-Container"

_TRUSTED_PROXY_NETS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
)


def is_trusted_proxy(request: Request) -> bool:
    """True when the TCP peer is the local reverse proxy (Caddy)."""
    peer = request.ip
    if not peer:
        return False
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(addr in net for net in _TRUSTED_PROXY_NETS)


def client_ip(request: Request) -> str:
    if not is_trusted_proxy(request):
        return request.ip or "unknown"
    forwarded = request.headers.get("X-Forwarded-For") or request.headers.get(
        "X-Real-IP"
    )
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.ip or "unknown"


def strip_untrusted_proxy_headers(request: Request) -> None:
    """Drop Caddy-only headers before handlers run if the client did not come via proxy."""
    if is_trusted_proxy(request):
        return
    for name in (HIKKAHOST_CONTAINER_HEADER, "X-Hikkahost-Image"):
        if name in request.headers:
            del request.headers[name]


def is_secure_request(request: Request) -> bool:
    if request.scheme == "https":
        return True
    if not is_trusted_proxy(request):
        return False
    forwarded = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip()
    return forwarded.lower() == "https"
