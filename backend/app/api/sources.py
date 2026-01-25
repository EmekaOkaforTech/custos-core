from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.ingestion_job import IngestionJob
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.source_record import SourceRecord

router = APIRouter(prefix="/api/sources", tags=["sources"])


class MoveCaptureRequest(BaseModel):
    meeting_id: str = Field(min_length=1)


@router.patch("/{source_id}/move")
def move_capture(source_id: str, payload: MoveCaptureRequest, db: Session = Depends(get_db)) -> dict:
    source = db.get(SourceRecord, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Capture not found")
    meeting = db.get(Meeting, payload.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if source.meeting_id == payload.meeting_id:
        return {"moved": False, "reason": "already_assigned"}

    old_meeting_id = source.meeting_id
    source.meeting_id = payload.meeting_id

    jobs = db.query(IngestionJob).filter(IngestionJob.source_id == source_id).all()
    for job in jobs:
        job.meeting_id = payload.meeting_id

    participants = (
        db.query(MeetingParticipant.person_id)
        .filter(MeetingParticipant.meeting_id == old_meeting_id)
        .all()
    )
    existing = (
        db.query(MeetingParticipant.person_id)
        .filter(MeetingParticipant.meeting_id == payload.meeting_id)
        .all()
    )
    existing_ids = {pid for (pid,) in existing}
    for (person_id,) in participants:
        if person_id in existing_ids:
            continue
        db.add(MeetingParticipant(meeting_id=payload.meeting_id, person_id=person_id))

    db.commit()
    return {"moved": True}
