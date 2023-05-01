from functools import wraps
from sanic.response import json
from config import Config


def protect(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        request = args[0]
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return json({"error": "Authorization header is missing."}, status=401)
        
        if auth_header != Config.SECRET_KEY:
            return json({"error": "Invalid token."}, status=401)

        return await f(*args, **kwargs)

    return wrapper
