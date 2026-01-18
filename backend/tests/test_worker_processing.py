def test_worker_processes_job(test_app):
    from datetime import datetime
    from uuid import uuid4

    from app.db import SessionLocal, init_db
    from app.ingestion import worker
    from app.models.commitment import Commitment
    from app.models.ingestion_job import IngestionJob
    from app.models.risk_flag import RiskFlag
    from app.models.source_record import SourceRecord

    init_db()
    session = SessionLocal()
    try:
        job_id = f"j_{uuid4().hex}"
        job = IngestionJob(
            id=job_id,
            meeting_id="m_1",
            payload="Blocked by vendor, due Friday\n- Send update\n",
            capture_type="notes",
            status="queued",
            created_at=datetime.utcnow(),
        )
        session.add(job)
        session.commit()
    finally:
        session.close()

    worker.run_once()

    session = SessionLocal()
    try:
        job = session.get(IngestionJob, job_id)
        assert job.status == "succeeded"
        source = session.query(SourceRecord).first()
        commitment = session.query(Commitment).first()
        flags = session.query(RiskFlag).all()
        assert source is not None
        assert commitment is not None
        assert commitment.text == "Blocked by vendor, due Friday"
        assert len(flags) == 2
        flag_types = {flag.flag_type for flag in flags}
        assert flag_types == {"deadline_reference", "blocker_reference"}
    finally:
        session.close()
