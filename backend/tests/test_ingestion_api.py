def test_ingestion_endpoint_persists_payload(test_app):
    from fastapi.testclient import TestClient

    from app.db import init_db

    init_db()
    client = TestClient(test_app)
    payload = {
        "meeting_id": "m_123",
        "capture_type": "notes",
        "payload": "Sample meeting notes",
    }
    response = client.post("/api/ingestion", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = client.get(f"/api/ingestion/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "queued"

    from app.db import SessionLocal
    from app.models.ingestion_job import IngestionJob

    session = SessionLocal()
    try:
        job = session.get(IngestionJob, job_id)
        assert job is not None
        assert job.payload == "Sample meeting notes"
    finally:
        session.close()
