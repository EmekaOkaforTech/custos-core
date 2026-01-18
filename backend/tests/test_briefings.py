def seed_meeting(session, title, starts_at, source_age_days=None):
    from datetime import datetime, timedelta
    from uuid import uuid4

    from app.models.commitment import Commitment
    from app.models.meeting import Meeting
    from app.models.source_record import SourceRecord

    meeting_id = f"m_{uuid4().hex}"
    meeting = Meeting(
        id=meeting_id,
        title=title,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
    )
    session.add(meeting)
    if source_age_days is not None:
        source_id = f"s_{uuid4().hex}"
        source = SourceRecord(
            id=source_id,
            meeting_id=meeting_id,
            captured_at=datetime.utcnow() - timedelta(days=source_age_days),
            capture_type="notes",
            uri=f"local://sources/{source_id}",
        )
        session.add(source)
        commitment = Commitment(
            id=f"c_{uuid4().hex}",
            text="Follow up",
            due_at=None,
            acknowledged=False,
            source_id=source_id,
        )
        session.add(commitment)
    session.commit()
    return meeting_id


def test_briefings_today_order_and_status(test_app):
    from datetime import datetime, timedelta

    from app.db import SessionLocal, init_db
    from fastapi.testclient import TestClient

    init_db()
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        day_start = datetime(now.year, now.month, now.day)
        seed_meeting(session, "Earlier", day_start + timedelta(hours=9), source_age_days=1)
        seed_meeting(session, "Later", day_start + timedelta(hours=10), source_age_days=20)
        seed_meeting(session, "Missing", day_start + timedelta(hours=11), source_age_days=None)
    finally:
        session.close()

    client = TestClient(test_app)
    response = client.get("/api/briefings/today")
    assert response.status_code == 200
    meetings = response.json()["meetings"]
    assert meetings[0]["title"] == "Earlier"
    assert meetings[1]["title"] == "Later"
    assert meetings[2]["title"] == "Missing"
    statuses = [meeting["status"] for meeting in meetings]
    assert statuses == ["ok", "stale", "missing"]


def test_briefings_next_includes_source(test_app):
    from datetime import datetime, timedelta

    from app.db import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        seed_meeting(session, "Next", now + timedelta(hours=1), source_age_days=2)
    finally:
        session.close()

    from fastapi.testclient import TestClient

    client = TestClient(test_app)
    response = client.get("/api/briefings/next")
    assert response.status_code == 200
    data = response.json()
    assert data["cards"][0]["source"]["id"]
    assert data["cards"][0]["source"]["uri"].startswith("local://")
