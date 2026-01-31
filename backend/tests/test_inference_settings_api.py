from fastapi.testclient import TestClient


def test_inference_settings_roundtrip(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    payload = {"inference_url": "http://192.168.1.50:8080", "inference_enabled": True}
    response = client.put("/api/inference/settings", json=payload)
    assert response.status_code == 200

    stored = client.get("/api/inference/settings")
    assert stored.status_code == 200
    data = stored.json()
    assert data["inference_url"] == payload["inference_url"]
    assert data["inference_enabled"] is True
