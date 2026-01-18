def test_status_endpoint_reports_health(test_app):
    from datetime import datetime
    from uuid import uuid4

    from fastapi.testclient import TestClient

    from app.db import SessionLocal, init_db
    from app.models.ingestion_job import IngestionJob

    init_db()
    session = SessionLocal()
    try:
        job = IngestionJob(
            id=f"j_{uuid4().hex}",
            meeting_id="m_1",
            payload="payload",
            capture_type="notes",
            status="failed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error="processing_error",
        )
        session.add(job)
        session.commit()
    finally:
        session.close()

    client = TestClient(test_app)
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["health"] == "attention"
    assert data["db_encrypted"] is False
