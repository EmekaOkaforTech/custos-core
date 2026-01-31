from fastapi.testclient import TestClient


def test_calendar_connection_create_and_get(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    payload = {
        "provider": "demo",
        "scopes": ["events.read", "attendees.read"],
        "token": "secret-token",
        "enabled": True,
    }
    create = client.post("/api/calendar/connection", json=payload)
    assert create.status_code == 200
    data = create.json()
    assert data["connected"] is True
    assert data["provider"] == "demo"
    assert data["scopes"] == payload["scopes"]
    assert "token" not in data

    get_resp = client.get("/api/calendar/connection")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["connected"] is True
    assert get_data["provider"] == "demo"
    assert get_data["scopes"] == payload["scopes"]
    assert "token" not in get_data


def test_calendar_connection_invalid_provider(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    create = client.post(
        "/api/calendar/connection",
        json={"provider": "unknown", "scopes": [], "token": "x", "enabled": True},
    )
    assert create.status_code == 422


def test_calendar_connection_blank_token_or_scopes(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    missing_scopes = client.post(
        "/api/calendar/connection",
        json={"provider": "demo", "scopes": [], "token": "x", "enabled": True},
    )
    assert missing_scopes.status_code == 422
    blank_token = client.post(
        "/api/calendar/connection",
        json={"provider": "demo", "scopes": ["events.read"], "token": "   ", "enabled": True},
    )
    assert blank_token.status_code == 422
