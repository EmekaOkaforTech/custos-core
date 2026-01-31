from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_move_capture_between_meetings(test_app):
    from app.db import SessionLocal, init_db
    from app.models.ingestion_job import IngestionJob
    from app.models.meeting import Meeting
    from app.models.source_record import SourceRecord

    init_db()
    session = SessionLocal()
    try:
        meeting_a = Meeting(
            id="m_move_a",
            title="Meeting A",
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(hours=1),
            source="manual",
        )
        meeting_b = Meeting(
            id="m_move_b",
            title="Meeting B",
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(hours=1),
            source="manual",
        )
        source = SourceRecord(
            id="s_move_1",
            meeting_id="m_move_a",
            captured_at=datetime.utcnow(),
            capture_type="notes",
            uri="local://sources/s_move_1",
        )
        job = IngestionJob(
            id="j_move_1",
            meeting_id="m_move_a",
            payload="test",
            capture_type="notes",
            status="succeeded",
            source_id="s_move_1",
        )
        session.add_all([meeting_a, meeting_b, source, job])
        session.commit()
    finally:
        session.close()

    client = TestClient(test_app)
    response = client.patch("/api/sources/s_move_1/move", json={"meeting_id": "m_move_b"})
    assert response.status_code == 200
    data = response.json()
    assert data["moved"] is True
