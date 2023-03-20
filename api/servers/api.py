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
    get_number_of_containers
)

api = Blueprint('event', url_prefix='/host')


@api.route('/ping', methods=['GET'])
async def ping(request):
    return json({'message': 'pong'})


@api.route('/create/<name>/<port>', methods=['GET'])
@protect
async def create_api(request, port, name):
    try:
        create(port, name)
        return json({'message': 'created'})
    except Exception as e:
        return json({'error': str(e)}, status=400)
    
@api.route('/action/<type>/<name>', methods=['GET'])
@protect
async def action_api(request, type, name):
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
    try:
        return json({'list': containers_list()})
    except Exception as e:
        return json({'error': str(e)}, status=400)
    
@api.route('/number', methods=['GET'])
@protect
async def number_api(request):
    try:
        return json({'number': get_number_of_containers()})
    except Exception as e:
        return json({'error': str(e)}, status=400)