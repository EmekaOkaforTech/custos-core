from fastapi.testclient import TestClient


def test_nas_backup_target_roundtrip(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)

    default = client.get("/api/backup/target")
    assert default.status_code == 200

    payload = {
        "protocol": "smb",
        "host": "192.168.1.10",
        "share": "backups",
        "mount_path": "/tmp/custos-nas",
        "username": "dev",
        "password": "secret",
        "enabled": True,
    }
    response = client.put("/api/backup/target", json=payload)
    assert response.status_code == 200

    stored = client.get("/api/backup/target")
    assert stored.status_code == 200
    data = stored.json()
    assert data["protocol"] == "smb"
    assert data["mount_path"] == "/tmp/custos-nas"
    assert data["enabled"] is True
