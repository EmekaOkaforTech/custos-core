import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _reload_admin_modules():
    for module_name in ["app.settings", "app.security", "app.api.admin", "app.main"]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])


def test_admin_bootstrap_rotation(tmp_path):
    os.environ["CUSTOS_ADMIN_API_ENABLED"] = "1"
    os.environ["CUSTOS_ENV"] = "dev"
    os.environ["CUSTOS_ADMIN_BOOTSTRAP_KEY"] = "bootstrap-key"
    os.environ["CUSTOS_DATA_DIR"] = str(Path(tmp_path) / "data")
    _reload_admin_modules()

    from app.main import app

    client = TestClient(app)

    settings = client.get("/api/admin/settings")
    assert settings.status_code == 200
    assert settings.json()["key_configured"] is False

    rotate = client.post(
        "/api/admin/api-key/rotate",
        headers={"X-API-Key": "bootstrap-key"},
        json={"new_key": "new-admin-key"},
    )
    assert rotate.status_code == 200

    settings_new = client.get("/api/admin/settings", headers={"X-API-Key": "new-admin-key"})
    assert settings_new.status_code == 200

    settings_old = client.get("/api/admin/settings", headers={"X-API-Key": "bootstrap-key"})
    assert settings_old.status_code == 401
