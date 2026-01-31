from fastapi.testclient import TestClient


def test_sync_settings_roundtrip(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    payload = {"mount_path": "/tmp/custos-sync", "enabled": True}
    response = client.put("/api/sync/settings", json=payload)
    assert response.status_code == 200

    stored = client.get("/api/sync/settings")
    assert stored.status_code == 200
    data = stored.json()
    assert data["mount_path"] == payload["mount_path"]
    assert data["enabled"] is True
