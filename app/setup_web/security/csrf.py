import hmac
import secrets

from sanic import Request
from sanic.response import JSONResponse

from app.setup_web.security.proxy import is_secure_request

CSRF_COOKIE = "setup_web_csrf"
CSRF_HEADER = "X-CSRF-Token"

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def ensure_csrf(request: Request) -> None:
    if request.method not in MUTATING_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise PermissionError("csrf_invalid")


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def attach_csrf_cookie(response: JSONResponse, token: str, request: Request) -> None:
    """Set CSRF cookie on a JSON response (Sanic 22 uses response.cookies)."""
    response.cookies[CSRF_COOKIE] = token
    response.cookies[CSRF_COOKIE]["httponly"] = True
    response.cookies[CSRF_COOKIE]["samesite"] = "Lax"
    response.cookies[CSRF_COOKIE]["path"] = "/"
    if is_secure_request(request):
        response.cookies[CSRF_COOKIE]["secure"] = True
