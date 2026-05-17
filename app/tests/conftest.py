import shutil
from pathlib import Path

import pytest

_CONFIG = Path(__file__).resolve().parents[1] / "config.py"
_EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.py"


@pytest.fixture(scope="session", autouse=True)
def _ensure_config():
    if not _CONFIG.exists() and _EXAMPLE.exists():
        shutil.copy(_EXAMPLE, _CONFIG)


@pytest.fixture
def app():
    from ..__main__ import app as api_app

    return api_app
