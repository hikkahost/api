from sanic import Sanic
from sanic.response import json
from app.handlers import api
from sanic_cors import CORS # , cross_origin
#from sanic_openapi import openapi2_blueprint, doc


app = Sanic('hh-api')
app.blueprint(api)
app.config["API_TITLE"] = "Hikka HOST API"
app.config["API_SECURITY"] = [{"ApiKeyAuth": []}]
app.config["API_SECURITY_DEFINITIONS"] = {
    "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}
}
app.config["API_SCHEMES"] = ["https", "http"]
#openapi2_blueprint.url_prefix = "/api/v1"
#app.blueprint(openapi2_blueprint)
CORS(app)


@app.route("/")
async def test(request):
    """
    Test route

    openapi:
    ---
    parameters:
      - name: limit
        in: query
        description: How many items to return at one time (max 100)
        required: true
    """
    return json({"hello": "world"})


@app.exception(Exception)
async def handle_exception(request, exception):
    return json({"error": str(exception)}, status=400)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, auto_reload=True)
