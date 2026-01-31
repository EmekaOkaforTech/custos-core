import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _reload_admin_modules():
    for module_name in ["app.settings", "app.security", "app.api.admin", "app.main"]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])


def test_admin_demo_reset(tmp_path):
    os.environ["CUSTOS_ADMIN_API_ENABLED"] = "1"
    os.environ["CUSTOS_ENV"] = "dev"
    os.environ["CUSTOS_ADMIN_BOOTSTRAP_KEY"] = "bootstrap-key"
    os.environ["CUSTOS_DATA_DIR"] = str(Path(tmp_path) / "data")
    _reload_admin_modules()

    from app.main import app

    client = TestClient(app)

    rotate = client.post(
        "/api/admin/api-key/rotate",
        headers={"X-API-Key": "bootstrap-key"},
        json={"new_key": "admin-key"},
    )
    assert rotate.status_code == 200

    reset = client.post(
        "/api/admin/demo/reset",
        headers={"X-API-Key": "admin-key"},
    )
    assert reset.status_code == 200
    assert reset.json()["status"] == "reset"

    people = client.get("/api/people")
    assert people.status_code == 200
    assert len(people.json()) >= 2
