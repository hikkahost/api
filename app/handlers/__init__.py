from app.handlers.servers.api import api as servers_api
from sanic import Blueprint

api = Blueprint.group(servers_api, url_prefix='/api', strict_slashes=True)
