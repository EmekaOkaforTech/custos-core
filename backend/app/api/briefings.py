from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.commitment import Commitment
from app.models.meeting import Meeting
from app.models.source_record import SourceRecord

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
        return {
            "meeting": None,
            "cards": [],
            "commitments": [],
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
    else:
        summary = "No recent context available."
        source_meta = None

    commitments = (
        db.query(Commitment)
        .join(SourceRecord, Commitment.source_id == SourceRecord.id)
        .filter(SourceRecord.meeting_id == meeting.id)
        .order_by(Commitment.due_at.asc().nulls_last(), Commitment.created_at.asc())
        .all()
    )

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
            }
        ],
        "commitments": [
            {
                "id": item.id,
                "text": item.text,
                "acknowledged": item.acknowledged,
                "source_id": item.source_id,
                "due_at": item.due_at,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in commitments
        ],
        "updated_at": now.isoformat(),
        "cached": cached,
        "offline": offline,
    }
