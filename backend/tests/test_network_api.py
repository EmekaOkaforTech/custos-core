from fastapi.testclient import TestClient


def test_network_services_manual_override(test_app):
    client = TestClient(test_app)
    payload = {
        "discovery_enabled": False,
        "scan_interval_minutes": 10,
        "manual_services": [
            {"type": "nas", "protocol": "smb", "host": "192.168.1.10", "port": 445}
        ],
    }
    resp = client.put("/api/network/settings", json=payload)
    assert resp.status_code == 200
    services = client.get("/api/network/services")
    assert services.status_code == 200
    data = services.json()
    assert "services" in data
    assert any(item["host"] == "192.168.1.10" for item in data["services"])


def test_network_settings_roundtrip(test_app):
    client = TestClient(test_app)
    payload = {
        "discovery_enabled": True,
        "scan_interval_minutes": 20,
        "manual_services": [],
    }
    resp = client.put("/api/network/settings", json=payload)
    assert resp.status_code == 200
    get_resp = client.get("/api/network/settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["discovery_enabled"] is True
    assert data["scan_interval_minutes"] == 20
