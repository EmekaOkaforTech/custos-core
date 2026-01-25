from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.source_record import SourceRecord

from app.db import get_db
from app.models.commitment import Commitment
from app.models.ingestion_job import IngestionJob

router = APIRouter(prefix="/api/commitments", tags=["commitments"])


class CommitmentAckRequest(BaseModel):
    acknowledged: bool


class CommitmentUpdateRequest(BaseModel):
    relevant_by: datetime | None = None


@router.get("/closure")
def commitment_closure(db: Session = Depends(get_db)) -> dict:
    now = datetime.utcnow()
    commitments = (
        db.query(Commitment, SourceRecord, Meeting)
        .join(SourceRecord, Commitment.source_id == SourceRecord.id)
        .join(Meeting, SourceRecord.meeting_id == Meeting.id)
        .order_by(Commitment.due_at.asc().nulls_last(), Commitment.created_at.asc())
        .all()
    )

    meeting_ids = {meeting.id for (_, _, meeting) in commitments}
    source_ids = {source.id for (_, source, _) in commitments}
    participants = (
        db.query(MeetingParticipant.meeting_id, Person.id, Person.name, Person.type)
        .join(Person, MeetingParticipant.person_id == Person.id)
        .filter(MeetingParticipant.meeting_id.in_(meeting_ids))
        .all()
    )
    people_by_meeting: dict[str, list[dict]] = {}
    for meeting_id, person_id, name, person_type in participants:
        people_by_meeting.setdefault(meeting_id, []).append(
            {"id": person_id, "name": name, "type": person_type}
        )

    job_payloads: dict[str, str] = {}
    if source_ids:
        jobs = (
            db.query(IngestionJob.source_id, IngestionJob.payload, IngestionJob.capture_type)
            .filter(IngestionJob.source_id.in_(source_ids))
            .all()
        )
        for source_id, payload, capture_type in jobs:
            if not source_id:
                continue
            job_payloads[source_id] = payload or ""

    items = []
    for commitment, source, meeting in commitments:
        due_at = commitment.due_at
        needs_attention = bool(due_at and due_at < now and not commitment.acknowledged)
        excerpt = None
        if source.id in job_payloads:
            raw = job_payloads[source.id].strip()
            excerpt = raw[:240] if raw else None
        items.append(
            {
                "id": commitment.id,
                "text": commitment.text,
                "acknowledged": commitment.acknowledged,
                "due_at": due_at,
                "created_at": commitment.created_at,
                "meeting": {
                    "id": meeting.id,
                    "title": meeting.title,
                    "starts_at": meeting.starts_at,
                },
                "source": {
                    "id": source.id,
                    "capture_type": source.capture_type,
                    "captured_at": source.captured_at,
                    "excerpt": excerpt,
                },
                "people": people_by_meeting.get(meeting.id, []),
                "needs_attention": needs_attention,
            }
        )

    return {"updated_at": now.isoformat(), "items": items}


@router.get("/threads")
def unresolved_threads(db: Session = Depends(get_db)) -> dict:
    now = datetime.utcnow()
    commitments = (
        db.query(Commitment, SourceRecord, Meeting)
        .join(SourceRecord, Commitment.source_id == SourceRecord.id)
        .join(Meeting, SourceRecord.meeting_id == Meeting.id)
        .filter(Commitment.acknowledged.is_(False))
        .order_by(Meeting.starts_at.asc(), Commitment.due_at.asc().nulls_last())
        .all()
    )
    if not commitments:
        return {"updated_at": now.isoformat(), "threads": []}

    meeting_ids = {meeting.id for (_, _, meeting) in commitments}
    source_ids = {source.id for (_, source, _) in commitments}

    participants = (
        db.query(MeetingParticipant.meeting_id, Person.id, Person.name, Person.type)
        .join(Person, MeetingParticipant.person_id == Person.id)
        .filter(MeetingParticipant.meeting_id.in_(meeting_ids))
        .all()
    )
    people_by_meeting: dict[str, list[dict]] = {}
    for meeting_id, person_id, name, person_type in participants:
        people_by_meeting.setdefault(meeting_id, []).append(
            {"id": person_id, "name": name, "type": person_type}
        )

    job_payloads: dict[str, str] = {}
    if source_ids:
        jobs = (
            db.query(IngestionJob.source_id, IngestionJob.payload, IngestionJob.capture_type)
            .filter(IngestionJob.source_id.in_(source_ids))
            .all()
        )
        for source_id, payload, _capture_type in jobs:
            if not source_id:
                continue
            job_payloads[source_id] = payload or ""

    threads = {}
    for commitment, source, meeting in commitments:
        thread = threads.setdefault(
            meeting.id,
            {
                "meeting": {
                    "id": meeting.id,
                    "title": meeting.title,
                    "starts_at": meeting.starts_at,
                },
                "people": people_by_meeting.get(meeting.id, []),
                "commitments": [],
                "excerpts": [],
            },
        )
        thread["commitments"].append(
            {
                "id": commitment.id,
                "text": commitment.text,
                "due_at": commitment.due_at,
                "created_at": commitment.created_at,
            }
        )
        if source.id not in {ex["source_id"] for ex in thread["excerpts"]}:
            raw = job_payloads.get(source.id, "").strip()
            thread["excerpts"].append(
                {
                    "source_id": source.id,
                    "capture_type": source.capture_type,
                    "captured_at": source.captured_at,
                    "excerpt": raw[:240] if raw else None,
                }
            )

    return {"updated_at": now.isoformat(), "threads": list(threads.values())}


@router.post("/{commitment_id}/ack")
def acknowledge_commitment(
    commitment_id: str,
    request: CommitmentAckRequest,
    db: Session = Depends(get_db),
) -> dict:
    commitment = db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    commitment.acknowledged = request.acknowledged
    db.commit()
    return {
        "id": commitment.id,
        "acknowledged": commitment.acknowledged,
        "updated_at": commitment.updated_at,
    }


@router.patch("/{commitment_id}")
def update_commitment(
    commitment_id: str,
    request: CommitmentUpdateRequest,
    db: Session = Depends(get_db),
) -> dict:
    commitment = db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    commitment.due_at = request.relevant_by
    db.commit()
    return {
        "id": commitment.id,
        "due_at": commitment.due_at,
        "updated_at": commitment.updated_at,
    }
