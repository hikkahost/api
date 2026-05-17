import logging
from pathlib import Path
from typing import Optional

from sanic import Sanic
from sanic.response import file, html, json

from app.setup_web.routes import setup
from app.setup_web.utils.static_paths import safe_static_file

logger = logging.getLogger(__name__)

STATIC_DIST = Path(__file__).resolve().parent / "static" / "dist"

_setup_web_app: Optional[Sanic] = None


def create_setup_web_app() -> Sanic:
    global _setup_web_app
    if _setup_web_app is not None:
        return _setup_web_app

    app = Sanic("hh-setup-web")
    app.config.TOUCHUP = False
    app.state.primary = False
    app.config.RESPONSE_TIMEOUT = 120
    app.blueprint(setup)

    if STATIC_DIST.exists():
        app.static("/assets", STATIC_DIST / "assets", name="setup_assets")

    @app.get("/")
    async def spa_index(request):
        index = STATIC_DIST / "index.html"
        if index.exists():
            return await file(index)
        return html(
            "<!DOCTYPE html><html><body style='background:#0a0a0a;color:#fff;"
            "font-family:sans-serif;padding:2rem'>"
            "<h1>HikkaHost Setup</h1><p>Frontend not built. Install Node.js "
            "and restart <code>python -m app</code>.</p></body></html>"
        )

    @app.get("/<path:path>")
    async def spa_fallback(request, path):
        if path.startswith("setup/"):
            return html("Not found", status=404)
        asset = safe_static_file(STATIC_DIST, path)
        if asset:
            return await file(asset)
        index = STATIC_DIST / "index.html"
        return await file(index) if index.exists() else html("Not found", status=404)

    @app.exception(Exception)
    async def handle_exception(request, exception):
        logger.exception("setup_web error: %s", exception)
        if request.path.startswith("/setup"):
            return json({"error": "internal_error"}, status=500)
        return html("Internal error", status=500)

    _setup_web_app = app
    return app
