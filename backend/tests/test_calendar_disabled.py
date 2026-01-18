def test_calendar_disabled_gate(monkeypatch, test_app):
    from app.calendar.demo_provider import DemoCalendarProvider
    from app.calendar.ingest import ingest_calendar
    from app.db import SessionLocal, init_db

    monkeypatch.setenv("CUSTOS_CALENDAR_ENABLED", "0")
    init_db()
    session = SessionLocal()
    try:
        result = ingest_calendar(DemoCalendarProvider(), session)
        assert result["status"] == "disabled"
    finally:
        session.close()
