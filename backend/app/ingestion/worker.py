import time
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.ingestion.rules import extract_commitments, extract_risk_flags
from app.models.commitment import Commitment
from app.models.ingestion_job import IngestionJob
import json

from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.risk_flag import RiskFlag
from app.models.source_record import SourceRecord

BACKOFF_SECONDS = 30
POLL_SECONDS = 2


def _eligible_failed_jobs(session: Session, now: datetime):
    cutoff = now - timedelta(seconds=BACKOFF_SECONDS)
    return (
        session.query(IngestionJob)
        .filter(IngestionJob.status == "failed", IngestionJob.completed_at <= cutoff)
        .all()
    )


def _next_queued_job(session: Session):
    return (
        session.query(IngestionJob)
        .filter(IngestionJob.status == "queued")
        .order_by(IngestionJob.created_at.asc())
        .first()
    )

def _normalize_payload(payload: str | None) -> str:
    if not payload:
        return ""
    return " ".join(payload.strip().split()).lower()


def _find_recent_duplicate(session: Session, job: IngestionJob, window_seconds: int = 300):
    if not job.payload:
        return None
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    normalized = _normalize_payload(job.payload)
    candidates = (
        session.query(IngestionJob)
        .filter(IngestionJob.status == "succeeded")
        .filter(IngestionJob.completed_at != None)  # noqa: E711
        .filter(IngestionJob.completed_at >= cutoff)
        .filter(IngestionJob.meeting_id == job.meeting_id)
        .filter(IngestionJob.capture_type == job.capture_type)
        .filter(IngestionJob.people_ids == job.people_ids)
        .order_by(IngestionJob.completed_at.desc())
        .all()
    )
    for candidate in candidates:
        if _normalize_payload(candidate.payload) == normalized:
            return candidate
    return None


def _process_job(session: Session, job: IngestionJob):
    job.status = "running"
    job.started_at = datetime.utcnow()
    session.commit()

    try:
        duplicate = _find_recent_duplicate(session, job)
        if duplicate and duplicate.source_id:
            job.status = "succeeded"
            job.completed_at = datetime.utcnow()
            job.source_id = duplicate.source_id
            job.error = "deduped"
            session.commit()
            return

        source_id = f"s_{uuid4().hex}"
        source = SourceRecord(
            id=source_id,
            meeting_id=job.meeting_id,
            captured_at=datetime.utcnow(),
            capture_type=job.capture_type,
            uri=f"local://sources/{source_id}",
        )
        session.add(source)
        job.source_id = source_id

        commitments = extract_commitments(job.payload)
        for item in commitments:
            commitment = Commitment(
                id=f"c_{uuid4().hex}",
                text=item.text,
                due_at=None,
                acknowledged=False,
                source_id=source_id,
                rule_id=item.rule_id,
            )
            session.add(commitment)

        flags = extract_risk_flags(job.payload)
        for flag in flags:
            risk_flag = RiskFlag(
                id=f"rf_{uuid4().hex}",
                source_id=source_id,
                flag_type=flag.flag_type,
                rule_id=flag.rule_id,
                excerpt=flag.excerpt,
                captured_at=source.captured_at,
            )
            session.add(risk_flag)

        session.flush()

        if job.people_ids:
            try:
                people_ids = json.loads(job.people_ids)
            except json.JSONDecodeError:
                people_ids = []
            for person_id in people_ids:
                if not person_id:
                    continue
                person = session.get(Person, person_id)
                if not person:
                    continue
                link = (
                    session.query(MeetingParticipant)
                    .filter_by(meeting_id=job.meeting_id, person_id=person_id)
                    .first()
                )
                if not link:
                    session.add(MeetingParticipant(meeting_id=job.meeting_id, person_id=person_id))

        participant_ids = (
            session.query(MeetingParticipant.person_id)
            .filter(MeetingParticipant.meeting_id == job.meeting_id)
            .all()
        )
        if participant_ids:
            now = datetime.utcnow()
            session.query(Person).filter(Person.id.in_([pid for (pid,) in participant_ids])).update(
                {Person.last_interaction_at: now}, synchronize_session=False
            )

        job.status = "succeeded"
        job.completed_at = datetime.utcnow()
        session.commit()
    except Exception:
        session.rollback()
        job.status = "failed"
        job.error = "processing_error"
        job.completed_at = datetime.utcnow()
        session.commit()


def run_once():
    init_db()
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        for failed in _eligible_failed_jobs(session, now):
            failed.status = "queued"
            failed.error = None
        session.commit()

        job = _next_queued_job(session)
        if job:
            _process_job(session, job)
    finally:
        session.close()


def run_forever():
    while True:
        run_once()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
