from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_ingestion_links_people_to_meeting(test_app):
    from app.db import SessionLocal, init_db
    from app.ingestion import worker
    from app.models.meeting import Meeting
    from app.models.person import Person

    init_db()
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        meeting = Meeting(
            id="m_loop_1",
            title="Loop Meeting",
            starts_at=now + timedelta(hours=2),
            ends_at=now + timedelta(hours=3),
            source="manual",
        )
        person = Person(id="p_loop_1", name="Loop Person", type="person")
        session.add(meeting)
        session.add(person)
        session.commit()
    finally:
        session.close()

    client = TestClient(test_app)
    payload = {
        "meeting_id": "m_loop_1",
        "capture_type": "notes",
        "payload": "Loop note",
        "people_ids": ["p_loop_1"],
    }
    response = client.post("/api/ingestion", json=payload)
    assert response.status_code == 202

    worker.run_once()

    briefing = client.get("/api/briefings/next")
    assert briefing.status_code == 200
    data = briefing.json()
    assert data["meeting"]["id"] == "m_loop_1"
    reason_people = data["cards"][0]["reason"]["people"]
    assert any(person["name"] == "Loop Person" for person in reason_people)
