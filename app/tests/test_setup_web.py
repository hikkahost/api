import json
from pathlib import Path

import pytest

from app.setup_web.utils import suggest_bot_username, user_profile
from app.setup_web.userbots import (
    delete_account,
    list_accounts,
    userbot_from_image,
    validate_container_name,
)
from app.setup_web.provision import (
    apply_credentials,
    coerce_api_hash,
    coerce_api_id,
    merge_credentials,
    merge_user_config,
    validate_api_hash,
)
from app.setup_web.utils.bot_username import validate_bot_username


def test_userbot_from_image():
    assert userbot_from_image("fajox/hikkahost:heroku").tag == "heroku"
    assert userbot_from_image("fajox/hikkahost:legacy").prefix == "legacy"


def test_validate_api_hash():
    assert validate_api_hash("b18441a1ff607e10a989891a5462e627")
    assert not validate_api_hash("short")


def test_user_profile_escapes_display_name():
    class FakeUser:
        id = 123
        username = "test<script>"
        first_name = "Ann"
        last_name = None

    payload = user_profile(FakeUser())
    assert payload["display_name"] == "Ann (@test&lt;script&gt;)"
    assert "&lt;" in payload["username"]


def test_suggest_bot_username():
    name = suggest_bot_username("heroku")
    assert name.startswith("heroku_")
    assert name.endswith("_bot")
    assert len(name) == len("heroku_") + 6 + len("_bot")


def test_coerce_api_credentials():
    assert coerce_api_id(None) == 2040
    assert coerce_api_id("") == 2040
    assert coerce_api_id("12345") == 12345
    assert coerce_api_id("bad") == 2040
    assert coerce_api_id(float("inf")) == 2040
    assert coerce_api_id(1e400) == 2040


@pytest.mark.asyncio
async def test_render_qr_data_uri():
    from app.setup_web.utils.qr_render import render_qr_data_uri

    payload = await render_qr_data_uri("tg://login?token=test")
    assert payload["qr_image"].startswith("data:image/png;base64,")
    assert 0 < payload["qr_logo_ratio"] < 1


@pytest.mark.asyncio
async def test_accounts_with_bad_config(monkeypatch, tmp_path):
    from unittest.mock import MagicMock

    from app.setup_web.routes import accounts

    monkeypatch.chdir(tmp_path)
    data = tmp_path / "volumes" / "999" / "data"
    data.mkdir(parents=True)
    (data / "config.json").write_text(
        json.dumps(
            {"api_id": float("inf"), "api_hash": "b18441a1ff607e10a989891a5462e627"}
        )
    )
    (tmp_path / "volumes" / "999" / ".env").write_text("IMAGE=fajox/hikkahost:hikka\n")

    req = MagicMock()
    monkeypatch.setenv("SETUP_WEB_DEV_CONTAINER", "999")
    monkeypatch.setenv("SETUP_WEB_ALLOW_DEV", "1")
    req.headers = {"Host": "127.0.0.1"}
    resp = await accounts(req)
    assert resp.status == 200


@pytest.mark.asyncio
async def test_list_accounts_malformed_inline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "volumes" / "42" / "data"
    data.mkdir(parents=True)
    (tmp_path / "volumes" / "42" / ".env").write_text("IMAGE=fajox/hikkahost:heroku\n")
    (data / "heroku-100.session").write_text("")
    (data / "config-100.json").write_text(
        json.dumps(
            {"heroku.inline": "not-a-dict", "hikka.inline": {"custom_bot": "ok_bot"}}
        )
    )
    userbot = userbot_from_image("fajox/hikkahost:heroku")
    items = await list_accounts("42", userbot)
    assert len(items) == 1
    assert items[0]["tg_id"] == 100
    assert items[0]["bot_username"] == "ok_bot"


def test_bot_username_invalid_chars():
    from app.setup_web.utils.bot_username import _validate_format

    with pytest.raises(ValueError, match="bot_username_invalid_chars"):
        _validate_format("my_bot$")
    with pytest.raises(ValueError, match="bot_username_invalid_chars"):
        _validate_format("привет_bot")


@pytest.mark.asyncio
async def test_bot_username_taken_in_container(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "volumes" / "55" / "data"
    data.mkdir(parents=True)
    (data / "heroku-1.session").write_text("")
    (data / "config-1.json").write_text(
        json.dumps({"heroku.inline": {"custom_bot": "taken_bot"}})
    )

    async def _telegram_free(_container, _username):
        return None

    monkeypatch.setattr(
        "app.setup_web.utils.bot_username._check_telegram_available",
        _telegram_free,
    )
    with pytest.raises(ValueError, match="bot_username_taken"):
        await validate_bot_username("55", "taken_bot", tg_id=2)
    assert await validate_bot_username("55", "taken_bot", tg_id=1) == "taken_bot"


@pytest.mark.asyncio
async def test_bot_username_taken_on_telegram(monkeypatch, tmp_path):
    from unittest.mock import MagicMock

    from app.setup_web.auth.state import AuthState, set_state

    monkeypatch.chdir(tmp_path)
    (tmp_path / "volumes" / "77" / "data").mkdir(parents=True)

    client = MagicMock()
    client.is_connected.return_value = True
    set_state(
        "77",
        AuthState(container="77", tg_id=1, client=client),
    )

    async def _telegram_taken(_container, username):
        if username == "busy_bot":
            raise ValueError("bot_username_taken")

    monkeypatch.setattr(
        "app.setup_web.utils.bot_username._check_telegram_available",
        _telegram_taken,
    )
    with pytest.raises(ValueError, match="bot_username_taken"):
        await validate_bot_username("77", "busy_bot", tg_id=1)


@pytest.mark.asyncio
async def test_apply_credentials_writes_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    volumes = tmp_path / "volumes" / "12345" / "data"
    volumes.mkdir(parents=True)

    async def _not_running(_name: str) -> bool:
        return False

    monkeypatch.setattr(
        "app.setup_web.provision.container_is_running",
        _not_running,
    )
    cfg = await apply_credentials("12345", 99999, "b18441a1ff607e10a989891a5462e627")
    assert cfg["api_id"] == 99999
    saved = json.loads((volumes / "config.json").read_text())
    assert saved["api_hash"] == "b18441a1ff607e10a989891a5462e627"


@pytest.mark.asyncio
async def test_merge_credentials_and_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    volumes = tmp_path / "volumes" / "12345" / "data"
    volumes.mkdir(parents=True)
    (tmp_path / "volumes" / "12345" / ".env").write_text(
        "IMAGE=fajox/hikkahost:heroku\n"
    )
    await merge_credentials("12345", 2040, "b18441a1ff607e10a989891a5462e627")
    cfg = json.loads((volumes / "config.json").read_text())
    assert cfg["api_id"] == 2040
    userbot = userbot_from_image("fajox/hikkahost:heroku")
    await merge_user_config("12345", userbot, 999, "MyHelperBot")
    user_cfg = json.loads((volumes / "config-999.json").read_text())
    assert user_cfg["heroku.inline"]["custom_bot"] == "myhelperbot"


@pytest.mark.asyncio
async def test_delete_account(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "volumes" / "77" / "data"
    data.mkdir(parents=True)
    (data / "hikka-42.session").write_text("")
    (data / "config-42.json").write_text("{}")
    await delete_account("77", 42)
    assert not (data / "hikka-42.session").exists()
    assert not (data / "config-42.json").exists()


@pytest.mark.asyncio
async def test_delete_account_not_found(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "volumes" / "88" / "data").mkdir(parents=True)
    with pytest.raises(ValueError, match="account_not_found"):
        await delete_account("88", 999)


@pytest.mark.asyncio
async def test_list_accounts_empty(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "volumes" / "x" / "data").mkdir(parents=True)
    userbot = userbot_from_image("fajox/hikkahost:hikka")
    assert await list_accounts("x", userbot) == []


def test_validate_container_name():
    validate_container_name("12345")
    with pytest.raises(ValueError):
        validate_container_name("../evil")


def test_ensure_csrf():
    from unittest.mock import MagicMock

    from app.setup_web.security import CSRF_COOKIE, CSRF_HEADER, ensure_csrf

    request = MagicMock()
    request.method = "POST"
    request.cookies = {CSRF_COOKIE: "abc"}
    request.headers = {CSRF_HEADER: "abc"}
    ensure_csrf(request)

    request.headers = {CSRF_HEADER: "wrong"}
    with pytest.raises(PermissionError):
        ensure_csrf(request)


def test_attach_csrf_cookie():
    from unittest.mock import MagicMock

    from sanic.response import json

    from app.setup_web.security import CSRF_COOKIE, attach_csrf_cookie

    request = MagicMock()
    request.scheme = "http"
    request.headers = {}
    response = json({"csrf": "tok"})
    attach_csrf_cookie(response, "tok", request)
    cookie_repr = str(response.cookies[CSRF_COOKIE])
    assert "tok" in cookie_repr
    assert response.cookies[CSRF_COOKIE]["httponly"] is True
    assert response.cookies[CSRF_COOKIE]["path"] == "/"


def test_resolve_container_from_host(monkeypatch):
    from unittest.mock import MagicMock

    from app.config import SERVER
    from app.setup_web.security import resolve_container

    req = MagicMock()
    req.ip = "203.0.113.1"
    req.headers = {"Host": f"myuser.{SERVER}.hikka.host"}
    assert resolve_container(req) == "myuser"


def test_resolve_container_rejects_spoofed_header(monkeypatch):
    from unittest.mock import MagicMock

    from app.config import SERVER
    from app.setup_web.security import resolve_container

    req = MagicMock()
    req.ip = "127.0.0.1"
    req.headers = {
        "Host": f"real.{SERVER}.hikka.host",
        "X-Hikkahost-Container": "evil",
    }
    with pytest.raises(PermissionError, match="Container header mismatch"):
        resolve_container(req)


def test_strip_untrusted_proxy_headers():
    from unittest.mock import MagicMock

    from app.setup_web.security import (
        HIKKAHOST_CONTAINER_HEADER,
        strip_untrusted_proxy_headers,
    )

    req = MagicMock()
    req.ip = "203.0.113.1"
    req.headers = {
        HIKKAHOST_CONTAINER_HEADER: "evil",
        "X-Hikkahost-Image": "heroku",
    }
    strip_untrusted_proxy_headers(req)
    assert HIKKAHOST_CONTAINER_HEADER not in req.headers
    assert "X-Hikkahost-Image" not in req.headers


def test_safe_static_file_rejects_traversal():
    from app.setup_web.utils.static_paths import safe_static_file

    base = Path("/tmp/setup_web_static_test")
    base.mkdir(exist_ok=True)
    (base / "ok.txt").write_text("x")
    assert safe_static_file(base, "ok.txt") is not None
    assert safe_static_file(base, "../etc/passwd") is None
    assert safe_static_file(base, "foo/../../etc/passwd") is None


def test_is_secure_request():
    from unittest.mock import MagicMock

    from app.setup_web.security import is_secure_request

    req = MagicMock()
    req.scheme = "https"
    req.headers = {}
    assert is_secure_request(req) is True

    req.scheme = "http"
    req.ip = "127.0.0.1"
    req.headers = {"X-Forwarded-Proto": "https"}
    assert is_secure_request(req) is True

    req.headers = {}
    assert is_secure_request(req) is False
