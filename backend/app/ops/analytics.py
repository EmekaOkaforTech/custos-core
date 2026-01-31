import json
from datetime import datetime, date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AnalyticsDaily, Commitment, Meeting, Person, SourceRecord


def compute_daily_metrics(db: Session, day: date | None = None) -> AnalyticsDaily:
    target_day = day or datetime.utcnow().date()
    start = datetime.combine(target_day, datetime.min.time())
    end = datetime.combine(target_day + timedelta(days=1), datetime.min.time())

    total_meetings = db.query(func.count(Meeting.id)).scalar() or 0
    total_people = db.query(func.count(Person.id)).scalar() or 0
    total_sources = db.query(func.count(SourceRecord.id)).scalar() or 0
    daily_sources = (
        db.query(func.count(SourceRecord.id))
        .filter(SourceRecord.captured_at >= start, SourceRecord.captured_at < end)
        .scalar()
        or 0
    )
    total_commitments = db.query(func.count(Commitment.id)).scalar() or 0
    open_commitments = (
        db.query(func.count(Commitment.id))
        .filter(Commitment.acknowledged == False)
        .scalar()
        or 0
    )

    metrics = {
        "total_meetings": total_meetings,
        "total_people": total_people,
        "total_sources": total_sources,
        "daily_sources": daily_sources,
        "total_commitments": total_commitments,
        "open_commitments": open_commitments,
    }

    record = (
        db.query(AnalyticsDaily)
        .filter(AnalyticsDaily.day == target_day)
        .first()
    )
    if record:
        record.metrics = json.dumps(metrics)
    else:
        record = AnalyticsDaily(day=target_day, metrics=json.dumps(metrics))
        db.add(record)

    db.commit()
    return record
