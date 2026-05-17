from app.setup_web.security.container import (
    parse_container_from_host,
    resolve_container,
)
from app.setup_web.security.csrf import (
    CSRF_COOKIE,
    CSRF_HEADER,
    MUTATING_METHODS,
    attach_csrf_cookie,
    ensure_csrf,
    issue_csrf_token,
)
from app.setup_web.security.proxy import (
    HIKKAHOST_CONTAINER_HEADER,
    is_secure_request,
    is_trusted_proxy,
    strip_untrusted_proxy_headers,
)
from app.setup_web.security.rate_limit import rate_limit_middleware


def mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return "***"
    return phone[:2] + "***" + phone[-2:]


__all__ = [
    "CSRF_COOKIE",
    "CSRF_HEADER",
    "HIKKAHOST_CONTAINER_HEADER",
    "MUTATING_METHODS",
    "attach_csrf_cookie",
    "ensure_csrf",
    "is_secure_request",
    "is_trusted_proxy",
    "issue_csrf_token",
    "mask_phone",
    "parse_container_from_host",
    "rate_limit_middleware",
    "resolve_container",
    "strip_untrusted_proxy_headers",
]
