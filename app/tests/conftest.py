import pytest
from sanic import Sanic, response

from ..__main__ import app as sanic_app


@pytest.fixture
def app():
    return sanic_app
