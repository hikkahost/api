import asyncio
from functools import partial
from sanic import Blueprint
from sanic.response import json
from app.utils.task_queue import queue_service, TaskType, TaskStatus
from app.utils.decorators.auth import protect
from app.src.container import (
    containers_list,
    get_number_of_containers,
    logs,
    stats,
    inspect,
)
from app.utils.resources import get_server_resources

api = Blueprint("event", url_prefix="/host")

DEFAULT_USERBOT = "vsecoder/hikka:latest"
DEFAULT_PASSWORD = "$2b$12$nr213f0pJnQuCAdLnRTMeODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O"
ACTION_TYPES = {"start", "stop", "restart", "recreate"}


async def _run_blocking(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


def _arg_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _get_required_arg(request, key: str) -> str:
    value = _arg_value(request.args.get(key))
    if value is None:
        raise ValueError(f"Missing required parameter: {key}")
    return value


def _get_optional_arg(request, key: str, default: str) -> str:
    value = _arg_value(request.args.get(key))
    return value if value is not None else default


def _task_response(task_id: str):
    return json({"task_id": task_id, "status": TaskStatus.PENDING}, status=202)


@api.route("/ping", methods=["GET"])
async def ping(request):
    return json({"message": "pong"})


@api.route("/create", methods=["GET"])
@protect
async def create_api(request):
    """
    Create a container

    openapi:
    ---
    parameters:
      - name: port
        in: query
        description: Port to bind
        required: true
      - name: name
        in: query
        description: Name of the container
        required: true
      - name: userbot
        in: query
        description: Userbot to use
        required: false
      - name: password
        in: query
        description: Password hash for the basic auth
        required: false
    """
    try:
        port = _get_required_arg(request, "port")
        name = _get_required_arg(request, "name")
        userbot = _get_optional_arg(request, "userbot", DEFAULT_USERBOT)
        password = _get_optional_arg(request, "password", DEFAULT_PASSWORD)

        task_id = await queue_service.add_task(
            TaskType.CREATE,
            {
                "port": port,
                "name": name,
                "userbot": userbot,
                "password": password,
            },
        )
        return _task_response(task_id)
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/action", methods=["GET"])
@protect
async def action_api(request):
    """
    Perform an action on a container

    openapi:
    ---
    parameters:
      - name: type
        in: query
        description: Type of the action
        required: true
      - name: name
        in: query
        description: Name of the container
        required: true
    """
    try:
        action_type = _get_required_arg(request, "type")
        name = _get_required_arg(request, "name")
        if action_type not in ACTION_TYPES:
            return json({"error": "Unknown action type"}, status=400)
        task_id = await queue_service.add_task(
            TaskType.ACTION,
            {"type": action_type, "name": name},
        )
        return _task_response(task_id)
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/list", methods=["GET"])
@protect
async def list_api(request):
    """
    Get a list of containers
    """
    try:
        return json({"list": await _run_blocking(containers_list)})
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/number", methods=["GET"])
@protect
async def number_api(request):
    """
    Get a number of containers
    """
    try:
        return json({"number": await _run_blocking(get_number_of_containers)})
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/logs", methods=["GET"])
@protect
async def logs_api(request):
    """
    Get logs of a container

    openapi:
    ---
    parameters:
      - name: name
        in: query
        description: Name of the container
        required: true
    """
    try:
        name = _get_required_arg(request, "name")
        return json({"logs": await _run_blocking(logs, name)})
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/exec", methods=["GET"])
@protect
async def exec_api(request):
    """
    Execute a command in a container

    openapi:
    ---
    parameters:
      - name: name
        in: query
        description: Name of the container
        required: true
      - name: command
        in: query
        description: Command to execute
        required: true
    """
    try:
        name = _get_required_arg(request, "name")
        command = _get_required_arg(request, "command")
        task_id = await queue_service.add_task(
            TaskType.EXEC, {"name": name, "command": command}
        )
        return _task_response(task_id)
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/stats", methods=["GET"])
@protect
async def stats_api(request):
    """
    Get stats of a container

    openapi:
    ---
    parameters:
      - name: name
        in: query
        description: Name of the container
        required: true
    """
    try:
        name = _get_required_arg(request, "name")
        stats_result = await _run_blocking(stats, name)
        inspect_result = await _run_blocking(inspect, name)
        return json({"stats": stats_result, "inspect": inspect_result})
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/status", methods=["GET"])
@protect
async def status_api(request):
    """
    Get status of a container

    openapi:
    ---
    parameters:
      - name: name
        in: query
        description: Name of the container
        required: true
    """
    try:
        name = _get_required_arg(request, "name")
        if await _run_blocking(stats, name) is None:
            return json({"status": "stopped"})
        return json({"status": "running"})
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/resources", methods=["GET"])
async def resources_api(request):
    """
    Get resources of a server
    """
    try:
        return json({"resources": get_server_resources()})
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/remove", methods=["GET"])
@protect
async def remove_api(request):
    """
    Remove a container

    openapi:
    ---
    parameters:
      - name: name
        in: query
        description: Name of the container
        required: true
    """
    try:
        task_id = await queue_service.add_task(
            TaskType.REMOVE, {"name": _get_required_arg(request, "name")}
        )
        return _task_response(task_id)
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/update-password", methods=["GET"])
@protect
async def update_password_api(request):
    """
    Update the password of a container

    openapi:
    ---
    parameters:
      - name: name
        in: query
        description: Name of the container
        required: true
      - name: password
        in: query
        description: Password hash for the basic auth
        required: true
    """
    try:
        name = _get_required_arg(request, "name")
        password = _get_required_arg(request, "password")
        task_id = await queue_service.add_task(
            TaskType.UPDATE_PASSWORD, {"name": name, "password": password}
        )
        return _task_response(task_id)
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/tasks/<task_id>", methods=["GET"])
@protect
async def task_status_api(request, task_id):
    try:
        status = await queue_service.get_task_status(task_id)
        if not status:
            return json({"error": "Task not found"}, status=404)
        return json(status)
    except Exception as e:
        return json({"error": str(e)}, status=400)
