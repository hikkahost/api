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
    logs
)
from sanic_openapi import openapi2_blueprint, doc

api = Blueprint('event', url_prefix='/host')



@api.route('/ping', methods=['GET'])
async def ping(request):
    return json({'message': 'pong'})


@api.route('/create/<name>/<port>', methods=['GET'])
@protect
async def create_api(request, port, name):
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
        create(port, name)
        return json({'message': 'created'})
    except Exception as e:
        return json({'error': str(e)}, status=400)


@api.route('/action/<type>/<name>', methods=['GET'])
@protect
async def action_api(request, type, name):
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
    actions = {
        'start': start,
        'stop': stop,
        'restart': restart,
    }

    action = actions.get(type)

    try:
        action(name)
        return json({'message': 'action completed'})
    except Exception as e:
        return json({'error': str(e)}, status=400)


@api.route('/list', methods=['GET'])
@protect
async def list_api(request):
    """
    Get a list of containers
    """
    try:
        return json({'list': containers_list()})
    except Exception as e:
        return json({'error': str(e)}, status=400)


@api.route('/number', methods=['GET'])
@protect
async def number_api(request):
    """
    Get a number of containers
    """
    try:
        return json({'number': get_number_of_containers()})
    except Exception as e:
        return json({'error': str(e)}, status=400)
    
@api.route('/logs/<name>', methods=['GET'])
@protect
async def logs_api(request, name):
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
        return json({'logs': logs(name)})
    except Exception as e:
        return json({'error': str(e)}, status=400)