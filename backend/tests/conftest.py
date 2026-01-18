import importlib
import os
import sys
from pathlib import Path

import pytest

BACKEND_PATH = Path(__file__).resolve().parents[1]
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

os.environ.setdefault("CUSTOS_ALLOW_PLAINTEXT_DB", "1")
os.environ.setdefault("CUSTOS_DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("CUSTOS_DATABASE_KEY", "test-key")


def reload_app_modules():
    for module_name in ["app.settings", "app.db", "app.main"]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])


@pytest.fixture()
def test_app(tmp_path):
    db_path = Path(tmp_path) / "test.db"
    os.environ["CUSTOS_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["CUSTOS_ALLOW_PLAINTEXT_DB"] = "1"
    os.environ["CUSTOS_DATABASE_KEY"] = "test-key"
    reload_app_modules()
    from app.main import app

    return app
