from api.servers.api import api as servers_api
from sanic import Blueprint
from sanic_openapi import swagger_blueprint


api = Blueprint.group(servers_api, swagger_blueprint, url_prefix='/api', strict_slashes=True)
