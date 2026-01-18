def test_commitment_ack_audited(test_app):
    from datetime import datetime
    from uuid import uuid4

    from fastapi.testclient import TestClient

    from app.db import SessionLocal, init_db
    from app.models.audit_log import AuditLog
    from app.models.commitment import Commitment
    from app.models.meeting import Meeting
    from app.models.source_record import SourceRecord

    init_db()
    session = SessionLocal()
    try:
        meeting_id = f"m_{uuid4().hex}"
        source_id = f"s_{uuid4().hex}"
        commitment_id = f"c_{uuid4().hex}"
        now = datetime.utcnow()

        meeting = Meeting(
            id=meeting_id,
            title="Audit Meeting",
            starts_at=now,
            ends_at=now,
        )
        source = SourceRecord(
            id=source_id,
            meeting_id=meeting_id,
            captured_at=now,
            capture_type="notes",
            uri=f"local://sources/{source_id}",
        )
        commitment = Commitment(
            id=commitment_id,
            text="Confirm audit trail",
            due_at=None,
            acknowledged=False,
            source_id=source_id,
        )
        session.add(meeting)
        session.add(source)
        session.add(commitment)
        session.commit()
    finally:
        session.close()

    client = TestClient(test_app)
    response = client.post(f"/api/commitments/{commitment_id}/ack", json={"acknowledged": True})
    assert response.status_code == 200
    response = client.post(f"/api/commitments/{commitment_id}/ack", json={"acknowledged": False})
    assert response.status_code == 200

    session = SessionLocal()
    try:
        updates = (
            session.query(AuditLog)
            .filter(AuditLog.entity_type == "Commitment", AuditLog.action == "update")
            .all()
        )
        assert len(updates) >= 2
    finally:
        session.close()
