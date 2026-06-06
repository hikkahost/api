import logging

from sanic import Blueprint, Request
from sanic.response import json

from app.setup_web import auth, provision
from app.setup_web.docker_ops import restart_container
from app.setup_web.http import json_body, setup_api, tg_id_from_request
from app.setup_web.security import (
    attach_csrf_cookie,
    ensure_csrf,
    issue_csrf_token,
    rate_limit_middleware,
    resolve_container,
)
from app.setup_web.userbots import (
    default_api_hash,
    default_api_id,
    delete_account,
    list_accounts,
    userbot_for_container,
)
from app.setup_web.utils.bot_username import check_bot_username, suggest_bot_username

logger = logging.getLogger("setup_web")
setup = Blueprint("setup", url_prefix="/setup")


@setup.middleware("request")
async def setup_middleware(request: Request):
    blocked = rate_limit_middleware(request)
    if blocked:
        return blocked
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        try:
            ensure_csrf(request)
        except PermissionError:
            return json({"error": "csrf_invalid"}, status=403)
    return None


@setup.get("/csrf")
async def get_csrf(request: Request):
    token = issue_csrf_token()
    response = json({"csrf": token})
    attach_csrf_cookie(response, token, request)
    return response


@setup.get("/accounts")
@setup_api(internal_error="internal_error", log_event="accounts")
async def accounts(request: Request):
    container = resolve_container(request)
    userbot = await userbot_for_container(container)
    cfg = await provision.read_config_json(container)
    return json(
        {
            "accounts": await list_accounts(container, userbot),
            "userbot": userbot.tag,
            "credentials": {
                "api_id": provision.coerce_api_id(cfg.get("api_id")),
                "api_hash_set": bool(str(cfg.get("api_hash") or "").strip()),
            },
            "defaults": {
                "api_id": default_api_id(),
                "api_hash": default_api_hash(),
            },
        }
    )


@setup.delete("/accounts")
@setup.post("/accounts/delete")
@setup_api(internal_error="delete_failed", log_event="delete account")
async def accounts_delete(request: Request):
    container = resolve_container(request)
    tg_id = tg_id_from_request(request)
    await delete_account(container, tg_id)
    try:
        await restart_container(container)
    except Exception as exc:
        logger.exception(
            "delete_account restart container=%s tg_id=%s failed",
            container,
            tg_id,
        )
        raise RuntimeError("delete_failed") from exc
    logger.info("account deleted container=%s tg_id=%s", container, tg_id)
    return json({"ok": True, "tg_id": tg_id})


@setup.put("/credentials")
@setup_api(internal_error="credentials_apply_failed", log_event="credentials")
async def credentials(request: Request):
    container = resolve_container(request)
    body = json_body(request)
    api_id = provision.coerce_api_id(body.get("api_id"))
    api_hash = provision.coerce_api_hash(body.get("api_hash"))
    if not provision.validate_api_hash(api_hash):
        return json({"error": "api_hash must be 32 hex characters"}, status=400)
    cfg = await provision.apply_credentials(
        container,
        api_id,
        api_hash,
        body.get("app_name"),
    )
    logger.info("credentials applied container=%s api_id=%s", container, api_id)
    return json(
        {
            "ok": True,
            "api_id": cfg["api_id"],
            "app_name": cfg.get("app_name"),
            "restarted": True,
        }
    )


@setup.post("/auth/mode")
@setup_api()
async def auth_mode(request: Request):
    container = resolve_container(request)
    mode = json_body(request).get("mode", "phone")
    await auth.set_auth_mode(container, mode)
    return json({"ok": True, "mode": mode})


@setup.post("/phone/send")
@setup_api()
async def phone_send(request: Request):
    container = resolve_container(request)
    phone = json_body(request).get("phone", "").strip()
    if not phone:
        return json({"error": "phone required"}, status=400)
    await auth.phone_send(container, phone)
    return json({"ok": True})


@setup.post("/phone/verify")
@setup_api()
async def phone_verify(request: Request):
    container = resolve_container(request)
    body = json_body(request)
    result = await auth.phone_verify(
        container,
        str(body.get("code", "")).strip(),
        body.get("password"),
    )
    return json(result)


@setup.post("/qr/init")
@setup_api()
async def qr_init(request: Request):
    container = resolve_container(request)
    return json(await auth.qr_init(container))


@setup.get("/qr/poll")
@setup_api()
async def qr_poll(request: Request):
    container = resolve_container(request)
    return json(await auth.qr_poll(container))


@setup.post("/qr/2fa")
@setup_api()
async def qr_2fa(request: Request):
    container = resolve_container(request)
    password = json_body(request).get("password", "")
    return json(await auth.qr_2fa(container, password))


@setup.get("/bot/suggest")
@setup_api()
async def bot_suggest(request: Request):
    container = resolve_container(request)
    userbot = await userbot_for_container(container)
    return json({"username": suggest_bot_username(userbot.prefix)})


@setup.post("/bot/check")
@setup_api()
async def bot_check(request: Request):
    container = resolve_container(request)
    body = json_body(request)
    tg_id = body.get("tg_id")
    if tg_id is not None:
        tg_id = int(tg_id)
    result = await check_bot_username(
        container, body.get("username", ""), tg_id=tg_id
    )
    return json(result)


@setup.post("/finish")
@setup_api(internal_error="provision_failed", log_event="finish")
async def finish(request: Request):
    container = resolve_container(request)
    bot_username = json_body(request).get("bot_username", "")
    state = auth.get_state(container)
    if not state or not state.tg_id:
        raise ValueError("Not authenticated")
    await check_bot_username(container, bot_username, tg_id=state.tg_id)
    tg_id, memory = auth.take_memory_session(container)
    await provision.finish_provision(container, tg_id, memory, bot_username)
    logger.info("provision finish container=%s tg_id=%s", container, tg_id)
    return json({"ok": True, "tg_id": tg_id})
