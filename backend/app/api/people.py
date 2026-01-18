from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.source_record import SourceRecord

router = APIRouter(prefix="/api/people", tags=["people"])


@router.get("")
def list_people(db: Session = Depends(get_db)) -> list[dict]:
    people = db.query(Person).order_by(Person.name.asc()).all()
    return [
        {
            "id": person.id,
            "name": person.name,
            "type": person.type,
            "last_interaction_at": person.last_interaction_at,
        }
        for person in people
    ]


@router.get("/{person_id}/timeline")
def person_timeline(person_id: str, db: Session = Depends(get_db)) -> dict:
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    meetings = (
        db.query(Meeting)
        .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
        .filter(MeetingParticipant.person_id == person_id)
        .order_by(desc(Meeting.starts_at), Meeting.id.asc())
        .all()
    )

    timeline = []
    for meeting in meetings:
        source = (
            db.query(SourceRecord)
            .filter(SourceRecord.meeting_id == meeting.id)
            .order_by(SourceRecord.captured_at.desc())
            .first()
        )
        timeline.append(
            {
                "occurred_at": meeting.starts_at,
                "meeting_id": meeting.id,
                "meeting_title": meeting.title,
                "meeting_starts_at": meeting.starts_at,
                "source_id": source.id if source else None,
                "source_missing": source is None,
            }
        )

    return {
        "person": {
            "id": person.id,
            "name": person.name,
            "type": person.type,
            "last_interaction_at": person.last_interaction_at,
        },
        "timeline": timeline,
    }
