from sanic import Blueprint
from sanic.response import json
from utils.decorators.auth import protect
from datetime import *
from src.container import (
    create,
    stop,
    start,
    restart,
    containers_list,
    get_number_of_containers,
    logs,
    execute,
    stats,
    remove,
)
from sanic_openapi import openapi2_blueprint, doc
from utils.resources import get_server_resources

api = Blueprint("event", url_prefix="/host")


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
    """
    try:
        port, name = request.args["port"][0], request.args["name"][0]
        create(port, name)
        return json({"message": "created"})
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
    type = request.args["type"][0]

    actions = {"start": start, "stop": stop, "restart": restart}

    action = actions.get(type)

    try:
        name = request.args["name"][0]
        action_output = action(name)
        return (
            json(action_output)
            if action_output
            else json({"message": "action completed"})
        )
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/list", methods=["GET"])
@protect
async def list_api(request):
    """
    Get a list of containers
    """
    try:
        return json({"list": containers_list()})
    except Exception as e:
        return json({"error": str(e)}, status=400)


@api.route("/number", methods=["GET"])
@protect
async def number_api(request):
    """
    Get a number of containers
    """
    try:
        return json({"number": get_number_of_containers()})
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
        name = request.args["name"][0]
        return json({"logs": logs(name)})
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
        name = request.args["name"][0]
        command = request.args["command"][0]
        return json({"exec": execute(name, command)})
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
        name = request.args["name"][0]
        return json({"stats": stats(name)})
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
        name = request.args["name"][0]
        if stats(name) is None:
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
    """
    try:
        return json({"remove": remove(request.args["name"][0])})
    except Exception as e:
        return json({"error": str(e)}, status=400)
