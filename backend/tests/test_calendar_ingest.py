def test_calendar_ingest_populates_tables(monkeypatch, test_app):
    from app.calendar.demo_provider import DemoCalendarProvider
    from app.calendar.ingest import ingest_calendar
    from app.db import SessionLocal, init_db
    from app.models.meeting import Meeting
    from app.models.meeting_participant import MeetingParticipant
    from app.models.person import Person

    monkeypatch.setenv("CUSTOS_CALENDAR_ENABLED", "1")
    init_db()
    session = SessionLocal()
    try:
        result = ingest_calendar(DemoCalendarProvider(), session)
        assert result["status"] == "ok"
        meeting = session.query(Meeting).filter(Meeting.source == "calendar").first()
        assert meeting is not None
        participant = session.query(MeetingParticipant).first()
        assert participant is not None
        person = session.query(Person).first()
        assert person.last_interaction_at is not None
    finally:
        session.close()
