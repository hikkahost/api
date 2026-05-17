import logging
from functools import wraps
from typing import Awaitable, Callable, Optional

from sanic import Request
from sanic.response import HTTPResponse, json

logger = logging.getLogger("setup_web")


def json_body(request: Request) -> dict:
    body = request.json
    return body if isinstance(body, dict) else {}


def tg_id_from_request(request: Request) -> int:
    raw = request.args.get("tg_id")
    if raw is None:
        raw = json_body(request).get("tg_id")
    if raw is None:
        raise ValueError("tg_id required")
    return int(raw)


def setup_api(
    *,
    internal_error: Optional[str] = None,
    log_event: Optional[str] = None,
) -> Callable:
    """Map setup_web domain errors to JSON responses."""

    def decorator(handler: Callable[..., Awaitable[HTTPResponse]]):
        @wraps(handler)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                return await handler(request, *args, **kwargs)
            except PermissionError as exc:
                return json({"error": str(exc)}, status=403)
            except ValueError as exc:
                message = str(exc)
                status = 404 if message == "account_not_found" else 400
                return json({"error": message}, status=status)
            except RuntimeError as exc:
                return json({"error": str(exc)}, status=409)
            except Exception:
                if log_event:
                    logger.exception("%s", log_event)
                if internal_error:
                    return json({"error": internal_error}, status=500)
                raise

        return wrapper

    return decorator
