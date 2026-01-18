def test_status_action_runs_backup_and_audits(test_app, tmp_path):
    from fastapi.testclient import TestClient

    from app.db import SessionLocal, init_db
    from app.models.audit_log import AuditLog

    init_db()
    client = TestClient(test_app)
    response = client.post("/api/status/actions", json={"action": "run_backup"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"] in {"succeeded", "failed"}

    session = SessionLocal()
    try:
        audit_entries = (
            session.query(AuditLog)
            .filter(AuditLog.action == "run_backup")
            .all()
        )
        assert audit_entries
    finally:
        session.close()

    response_again = client.post("/api/status/actions", json={"action": "run_backup"})
    assert response_again.status_code == 200
