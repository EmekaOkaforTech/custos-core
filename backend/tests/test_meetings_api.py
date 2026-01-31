from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_create_meeting_defaults(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    response = client.post("/api/meetings", json={"title": "New Meeting"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Meeting"
    assert data["id"].startswith("m_")
    assert data["starts_at"]
    assert data["ends_at"]

    upcoming = client.get("/api/meetings", params={"range": "upcoming"})
    assert upcoming.status_code == 200
    assert any(item["id"] == data["id"] for item in upcoming.json()["meetings"])


def test_create_meeting_blank_title(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    response = client.post("/api/meetings", json={"title": "   "})
    assert response.status_code == 422


def test_list_meetings_ranges(test_app):
    from app.db import SessionLocal, init_db
    from app.models.meeting import Meeting

    init_db()
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        start_today = datetime(now.year, now.month, now.day) + timedelta(hours=9)
        meeting_today = Meeting(
            id="m_test_today",
            title="Today Meeting",
            starts_at=start_today,
            ends_at=start_today + timedelta(hours=1),
            source="manual",
        )
        meeting_future = Meeting(
            id="m_test_future",
            title="Future Meeting",
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=2, hours=1),
            source="manual",
        )
        session.add(meeting_today)
        session.add(meeting_future)
        session.commit()
    finally:
        session.close()

    client = TestClient(test_app)
    today_response = client.get("/api/meetings", params={"range": "today"})
    assert today_response.status_code == 200
    today_meetings = today_response.json()["meetings"]
    assert any(item["id"] == "m_test_today" for item in today_meetings)
    assert all(item["id"] != "m_test_future" for item in today_meetings)

    upcoming_response = client.get("/api/meetings", params={"range": "upcoming"})
    assert upcoming_response.status_code == 200
    upcoming_ids = [item["id"] for item in upcoming_response.json()["meetings"]]
    assert "m_test_future" in upcoming_ids


def test_list_meetings_invalid_range(test_app):
    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    response = client.get("/api/meetings", params={"range": "invalid"})
    assert response.status_code == 422


def test_update_meeting_title(test_app):
    from app.db import SessionLocal, init_db
    from app.models.meeting import Meeting

    init_db()
    session = SessionLocal()
    try:
        meeting = Meeting(
            id="m_update_1",
            title="Old Title",
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(hours=1),
            source="manual",
        )
        session.add(meeting)
        session.commit()
    finally:
        session.close()

    client = TestClient(test_app)
    response = client.patch("/api/meetings/m_update_1", json={"title": "New Title"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
