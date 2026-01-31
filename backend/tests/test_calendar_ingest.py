import os

from fastapi.testclient import TestClient


def test_calendar_ingest_disabled_flag(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    client.post(
        "/api/calendar/connection",
        json={
            "provider": "demo",
            "scopes": ["events.read"],
            "token": "demo-token",
            "enabled": True,
        },
    )
    os.environ["CUSTOS_CALENDAR_ENABLED"] = "0"
    response = client.post("/api/calendar/ingest")
    assert response.status_code == 200
    assert response.json()["status"] == "disabled"


def test_calendar_ingest_demo_provider(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    client.post(
        "/api/calendar/connection",
        json={
            "provider": "demo",
            "scopes": ["events.read"],
            "token": "demo-token",
            "enabled": True,
        },
    )
    os.environ["CUSTOS_CALENDAR_ENABLED"] = "1"
    response = client.post("/api/calendar/ingest")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "failed"}
