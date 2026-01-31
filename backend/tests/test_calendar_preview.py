from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_calendar_preview_demo_provider(test_app):
    from app.db import init_db, SessionLocal
    from app.models.meeting import Meeting

    init_db()
    client = TestClient(test_app)
    setup = client.post(
        "/api/calendar/connection",
        json={
            "provider": "demo",
            "scopes": ["events.read"],
            "token": "demo-token",
            "enabled": True,
        },
    )
    assert setup.status_code == 200

    response = client.get("/api/calendar/preview", params={"range": "upcoming"})
    assert response.status_code == 200
    data = response.json()
    assert data["range"] == "upcoming"
    assert data["events"], "expected demo events"
    first = data["events"][0]
    assert "title" in first and "starts_at" in first and "ends_at" in first
    assert "attendee_count" in first

    session = SessionLocal()
    try:
        meetings = session.query(Meeting).all()
        assert meetings == []
    finally:
        session.close()


def test_calendar_preview_invalid_range(test_app):
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
    response = client.get("/api/calendar/preview", params={"range": "invalid"})
    assert response.status_code == 422


def test_calendar_preview_requires_connection(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    response = client.get("/api/calendar/preview", params={"range": "today"})
    assert response.status_code == 400


def test_calendar_preview_disabled_connection(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    client.post(
        "/api/calendar/connection",
        json={
            "provider": "demo",
            "scopes": ["events.read"],
            "token": "demo-token",
            "enabled": False,
        },
    )
    response = client.get("/api/calendar/preview", params={"range": "today"})
    assert response.status_code == 400
