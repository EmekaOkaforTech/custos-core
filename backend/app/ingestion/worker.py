import time
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.ingestion.rules import extract_commitments, extract_risk_flags
import hashlib
from app.models.commitment import Commitment
from app.models.ingestion_job import IngestionJob
import json

from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.risk_flag import RiskFlag
from app.models.meeting import Meeting
from app.ops.qdrant_store import add_documents
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


def _dedupe_key(job: IngestionJob, normalized_payload: str) -> str:
    parts = [
        job.meeting_id,
        job.capture_type,
        normalized_payload,
        (job.people_ids or "").strip(),
        job.relevant_at.isoformat() if job.relevant_at else "",
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _find_recent_duplicate(session: Session, job: IngestionJob, window_seconds: int = 300):
    if not job.payload:
        return None
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    normalized = _normalize_payload(job.payload)
    dedupe_key = _dedupe_key(job, normalized)
    candidates = (
        session.query(IngestionJob)
        .filter(IngestionJob.status == "succeeded")
        .filter(IngestionJob.completed_at != None)  # noqa: E711
        .filter(IngestionJob.completed_at >= cutoff)
        .filter(IngestionJob.meeting_id == job.meeting_id)
        .filter(IngestionJob.capture_type == job.capture_type)
        .filter(IngestionJob.people_ids == job.people_ids)
        .filter(IngestionJob.relevant_at == job.relevant_at)
        .filter(IngestionJob.dedupe_key == dedupe_key)
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

        normalized_payload = _normalize_payload(job.payload)
        dedupe_key = _dedupe_key(job, normalized_payload)
        existing_source = (
            session.query(SourceRecord)
            .filter(SourceRecord.dedupe_key == dedupe_key)
            .first()
        )
        if existing_source:
            job.status = "succeeded"
            job.completed_at = datetime.utcnow()
            job.source_id = existing_source.id
            job.error = "deduped"
            job.dedupe_key = dedupe_key
            session.commit()
            return
        source_id = f"s_{uuid4().hex}"
        source = SourceRecord(
            id=source_id,
            meeting_id=job.meeting_id,
            captured_at=datetime.utcnow(),
            capture_type=job.capture_type,
            uri=f"local://sources/{source_id}",
            relevant_at=job.relevant_at,
            dedupe_key=dedupe_key,
            index_in_memory=bool(job.index_in_memory),
        )
        session.add(source)
        job.source_id = source_id
        job.dedupe_key = dedupe_key

        meeting = session.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        meeting_title = meeting.title if meeting else "Context"
        excerpt = (job.payload or "").strip()
        if len(excerpt) > 200:
            excerpt = f"{excerpt[:197]}…"
        should_index = job.index_in_memory if job.index_in_memory is not None else job.capture_type == "reflection"
        if should_index:
            try:
                add_documents(
                    documents=[job.payload or ""],
                    metadata=[
                        {
                            "source_id": source_id,
                            "meeting_id": job.meeting_id,
                            "meeting_title": meeting_title,
                            "captured_at": source.captured_at.isoformat(),
                            "capture_type": job.capture_type,
                            "excerpt": excerpt or "No capture excerpt available.",
                        }
                    ],
                    ids=[source_id],
                )
            except Exception as exc:
                # Vector indexing is best-effort and must never block ingestion.
                print(f"Vector indexing failed for {source_id}: {exc}")

        commitments = [] if job.capture_type == "reflection" else extract_commitments(job.payload)
        for item in commitments:
            existing_commitment = (
                session.query(Commitment)
                .filter(Commitment.source_id == source_id, Commitment.text == item.text)
                .first()
            )
            if existing_commitment:
                continue
            commitment = Commitment(
                id=f"c_{uuid4().hex}",
                text=item.text,
                due_at=job.commitment_relevant_by,
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
