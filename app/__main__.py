import asyncio
import logging
import os
from typing import Optional

from sanic import Sanic
from sanic.response import json
from sanic_cors import CORS

from app.handlers import api
from app.setup_web.app import create_setup_web_app
from app.setup_web.build import ensure_web_build

logger = logging.getLogger(__name__)

API_BIND_HOST = os.environ.get("API_BIND_HOST", "0.0.0.0")
SETUP_BIND_HOST = os.environ.get("SETUP_BIND_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8000"))
SETUP_PORT = int(os.environ.get("SETUP_PORT", "8001"))

_api_app: Optional[Sanic] = None


def create_api_app() -> Sanic:
    global _api_app
    if _api_app is not None:
        return _api_app

    app = Sanic("hh-api")
    app.config.TOUCHUP = False
    app.blueprint(api)
    app.config["API_TITLE"] = "Hikka HOST API"
    app.config["API_SECURITY"] = [{"ApiKeyAuth": []}]
    app.config["API_SECURITY_DEFINITIONS"] = {
        "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}
    }
    app.config["API_SCHEMES"] = ["https", "http"]
    CORS(app)

    @app.route("/")
    async def test(request):
        return json({"hello": "world"})

    @app.exception(Exception)
    async def handle_exception(request, exception):
        return json({"error": str(exception)}, status=400)

    _api_app = app
    return app


app = create_api_app()


async def _start(app: Sanic, host: str, port: int):
    server = await app.create_server(host=host, port=port, return_asyncio_server=True)
    await server.startup()
    return server


async def main():
    if SETUP_BIND_HOST not in ("127.0.0.1", "::1"):
        logger.warning(
            "SETUP_BIND_HOST=%s exposes setup_web on all interfaces",
            SETUP_BIND_HOST,
        )

    ensure_web_build()
    api_app = create_api_app()
    setup_app = create_setup_web_app()
    api_srv = await _start(api_app, API_BIND_HOST, API_PORT)
    setup_srv = await _start(setup_app, SETUP_BIND_HOST, SETUP_PORT)
    await asyncio.gather(api_srv.serve_forever(), setup_srv.serve_forever())


if __name__ == "__main__":
    asyncio.run(main())
