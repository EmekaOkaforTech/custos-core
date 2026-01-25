from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.commitment import Commitment
from app.models.meeting import Meeting
from app.models.source_record import SourceRecord
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person

router = APIRouter(prefix="/api/briefings", tags=["briefings"])

STALE_DAYS = 14


def _status_for(last_source_at: datetime | None, now: datetime) -> str:
    if not last_source_at:
        return "missing"
    if now - last_source_at > timedelta(days=STALE_DAYS):
        return "stale"
    return "ok"


@router.get("/today")
def get_today_briefings(
    db: Session = Depends(get_db),
    cached: bool = Query(False),
    offline: bool = Query(False),
    cached_at: datetime | None = Query(None),
) -> dict:
    now = cached_at or datetime.utcnow()
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)

    meetings = (
        db.query(Meeting)
        .filter(Meeting.starts_at >= start, Meeting.starts_at < end)
        .order_by(Meeting.starts_at.asc())
        .all()
    )

    results = []
    for meeting in meetings:
        source = (
            db.query(SourceRecord)
            .filter(SourceRecord.meeting_id == meeting.id)
            .order_by(SourceRecord.captured_at.desc())
            .first()
        )
        last_source_at = source.captured_at if source else None
        status = _status_for(last_source_at, now)
        commitments_count = (
            db.query(func.count(Commitment.id))
            .join(SourceRecord, Commitment.source_id == SourceRecord.id)
            .filter(SourceRecord.meeting_id == meeting.id)
            .scalar()
        )
        results.append(
            {
                "id": meeting.id,
                "title": meeting.title,
                "starts_at": meeting.starts_at,
                "status": status,
                "last_source_at": last_source_at,
                "open_commitments": commitments_count or 0,
            }
        )

    return {
        "date": start.date().isoformat(),
        "meetings": results,
        "updated_at": now.isoformat(),
        "cached": cached,
        "offline": offline,
    }


@router.get("/next")
def get_next_briefing(
    db: Session = Depends(get_db),
    cached: bool = Query(False),
    offline: bool = Query(False),
    cached_at: datetime | None = Query(None),
) -> dict:
    now = cached_at or datetime.utcnow()
    meeting = (
        db.query(Meeting)
        .filter(Meeting.starts_at >= now)
        .order_by(Meeting.starts_at.asc())
        .first()
    )

    if not meeting:
        future_relevant = (
            db.query(SourceRecord, Meeting)
            .join(Meeting, SourceRecord.meeting_id == Meeting.id)
            .filter(SourceRecord.relevant_at != None)  # noqa: E711
            .filter(SourceRecord.relevant_at >= now)
            .order_by(SourceRecord.relevant_at.asc())
            .all()
        )
        future_items = []
        for source, meeting_item in future_relevant:
            future_items.append(
                {
                    "source_id": source.id,
                    "capture_type": source.capture_type,
                    "captured_at": source.captured_at,
                    "relevant_at": source.relevant_at,
                    "meeting": {
                        "id": meeting_item.id,
                        "title": meeting_item.title,
                        "starts_at": meeting_item.starts_at,
                    },
                }
            )
        return {
            "meeting": None,
            "cards": [],
            "commitments": [],
            "future_relevant": future_items,
            "updated_at": now.isoformat(),
            "cached": cached,
            "offline": offline,
        }

    source = (
        db.query(SourceRecord)
        .filter(SourceRecord.meeting_id == meeting.id)
        .order_by(SourceRecord.captured_at.desc())
        .first()
    )

    last_source_at = source.captured_at if source else None
    status = _status_for(last_source_at, now)

    if source:
        summary = f"Context captured via {source.capture_type}."
        source_meta = {
            "id": source.id,
            "captured_at": source.captured_at,
            "capture_type": source.capture_type,
            "uri": source.uri,
        }
        rule_meta = {"id": "source_capture", "type": source.capture_type}
    else:
        summary = "No recent context available."
        source_meta = None
        rule_meta = {"id": "no_source", "type": "absence"}

    commitments = (
        db.query(Commitment)
        .join(SourceRecord, Commitment.source_id == SourceRecord.id)
        .filter(SourceRecord.meeting_id == meeting.id)
        .order_by(Commitment.due_at.asc().nulls_last(), Commitment.created_at.asc())
        .all()
    )

    people = (
        db.query(Person)
        .join(MeetingParticipant, MeetingParticipant.person_id == Person.id)
        .filter(MeetingParticipant.meeting_id == meeting.id)
        .order_by(Person.name.asc())
        .all()
    )
    people_meta = [{"id": person.id, "name": person.name, "type": person.type} for person in people]

    return {
        "meeting": {
            "id": meeting.id,
            "title": meeting.title,
            "starts_at": meeting.starts_at,
        },
        "cards": [
            {
                "summary": summary,
                "status": status,
                "last_source_at": last_source_at,
                "source": source_meta,
                "reason": {
                    "meeting": {
                        "id": meeting.id,
                        "title": meeting.title,
                        "starts_at": meeting.starts_at,
                    },
                    "source": source_meta,
                    "people": people_meta,
                    "rule": rule_meta,
                },
            }
        ],
        "commitments": [
            {
                "id": item.id,
                "text": item.text,
                "acknowledged": item.acknowledged,
                "source_id": item.source_id,
                "rule_id": item.rule_id,
                "due_at": item.due_at,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in commitments
        ],
        "future_relevant": [],
        "updated_at": now.isoformat(),
        "cached": cached,
        "offline": offline,
    }
