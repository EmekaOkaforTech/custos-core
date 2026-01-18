def test_people_timeline_order_and_source(test_app):
    from datetime import datetime, timedelta

    from fastapi.testclient import TestClient

    from app.db import SessionLocal, init_db
    from app.models.meeting import Meeting
    from app.models.meeting_participant import MeetingParticipant
    from app.models.person import Person
    from app.models.source_record import SourceRecord

    init_db()
    session = SessionLocal()
    try:
        person = Person(id="p_1", name="Alex", type="person", last_interaction_at=None)
        session.add(person)
        now = datetime.utcnow()

        meeting_new = Meeting(
            id="m_new",
            title="Recent Meeting",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            source="calendar",
        )
        meeting_old = Meeting(
            id="m_old",
            title="Older Meeting",
            starts_at=now - timedelta(days=1),
            ends_at=now - timedelta(days=1, hours=-1),
            source="calendar",
        )
        session.add(meeting_new)
        session.add(meeting_old)
        session.add(MeetingParticipant(meeting_id="m_new", person_id="p_1"))
        session.add(MeetingParticipant(meeting_id="m_old", person_id="p_1"))

        source = SourceRecord(
            id="s_new",
            meeting_id="m_new",
            captured_at=now,
            capture_type="notes",
            uri="local://sources/s_new",
        )
        session.add(source)
        session.commit()
    finally:
        session.close()

    client = TestClient(test_app)
    response = client.get("/api/people/p_1/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["timeline"][0]["meeting_id"] == "m_new"
    assert data["timeline"][0]["source_id"] == "s_new"
    assert data["timeline"][1]["source_missing"] is True
