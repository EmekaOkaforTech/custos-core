import csv
import io
import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AnalyticsDaily, Commitment, Meeting, MeetingParticipant, Person, SourceRecord
from app.ops.analytics import compute_daily_metrics

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _parse_days(days: int | None) -> datetime:
    return datetime.utcnow() - timedelta(days=days or 30)


@router.post("/refresh")
def refresh_analytics(db: Session = Depends(get_db)):
    record = compute_daily_metrics(db)
    return {"day": record.day.isoformat(), "metrics": json.loads(record.metrics)}


@router.get("/relationship-health")
def relationship_health(db: Session = Depends(get_db), window_days: int = 30):
    cutoff = _parse_days(window_days)
    people = db.query(Person).order_by(Person.name.asc()).all()
    items = []
    for person in people:
        count = (
            db.query(func.count(SourceRecord.id))
            .outerjoin(MeetingParticipant, MeetingParticipant.meeting_id == SourceRecord.meeting_id)
            .filter(
                SourceRecord.captured_at >= cutoff,
                (SourceRecord.person_id == person.id)
                | (MeetingParticipant.person_id == person.id),
            )
            .scalar()
            or 0
        )
        items.append({
            "person_id": person.id,
            "name": person.name,
            "count": count,
            "window_days": window_days,
        })
    return {"items": items, "window_days": window_days}


@router.get("/commitments")
def commitment_analytics(db: Session = Depends(get_db)):
    total = db.query(func.count(Commitment.id)).scalar() or 0
    acknowledged = db.query(func.count(Commitment.id)).filter(Commitment.acknowledged == True).scalar() or 0
    open_count = total - acknowledged
    completion_rate = (acknowledged / total) if total else 0
    avg_close_days = None
    if acknowledged:
        rows = db.query(Commitment).filter(Commitment.acknowledged == True).all()
        deltas = [(row.updated_at - row.created_at).days for row in rows if row.updated_at and row.created_at]
        if deltas:
            avg_close_days = sum(deltas) / len(deltas)
    return {
        "total": total,
        "acknowledged": acknowledged,
        "open": open_count,
        "completion_rate": completion_rate,
        "avg_close_days": avg_close_days,
    }


@router.get("/context-coverage")
def context_coverage(db: Session = Depends(get_db)):
    total_meetings = db.query(func.count(Meeting.id)).scalar() or 0
    meetings_with_sources = (
        db.query(func.count(func.distinct(SourceRecord.meeting_id)))
        .filter(SourceRecord.meeting_id.isnot(None))
        .scalar()
        or 0
    )
    meetings_without = max(total_meetings - meetings_with_sources, 0)
    stale_cutoff = datetime.utcnow() - timedelta(days=30)
    stale_people = db.query(Person).filter(
        (Person.last_interaction_at.is_(None)) | (Person.last_interaction_at < stale_cutoff)
    ).all()
    return {
        "total_meetings": total_meetings,
        "meetings_with_sources": meetings_with_sources,
        "meetings_without_sources": meetings_without,
        "stale_people": [{"id": p.id, "name": p.name} for p in stale_people],
    }


@router.post("/export")
def export_analytics(db: Session = Depends(get_db)):
    records = db.query(AnalyticsDaily).order_by(AnalyticsDaily.day.desc()).limit(30).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["day", "metrics"])
    for record in records:
        writer.writerow([record.day.isoformat(), record.metrics])
    return {"csv": output.getvalue()}
