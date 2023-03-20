from sanic import Sanic
from sanic.response import json
from api import *
from config import *
from sanic_cors import CORS, cross_origin
from sanic_openapi import openapi3_blueprint


app = Sanic(__name__)
app.blueprint(api)
app.blueprint(openapi3_blueprint)
CORS(app)


@app.route('/')
async def test(request):
    return json({'hello': 'world'})


@app.exception(Exception)
async def handle_exception(request, exception):
    return json({'error': str(exception)}, status=400)
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True, auto_reload=True)