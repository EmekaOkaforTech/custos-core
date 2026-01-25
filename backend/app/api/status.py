from datetime import datetime, timedelta
from uuid import uuid4

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.audit_log import AuditLog
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.source_record import SourceRecord
from app.models.ingestion_job import IngestionJob
from app.ops.backup import _status_path, create_backup
from app.settings import allow_plaintext_db
from app.calendar.status import read_status as read_calendar_status

router = APIRouter(prefix="/api", tags=["status"])


def _db_encrypted(db: Session) -> bool:
    if allow_plaintext_db():
        return False
    result = db.execute(text("PRAGMA cipher_version;")).fetchone()
    return bool(result and result[0])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return {"status": "ok", "db_encrypted": _db_encrypted(db)}


@router.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    now = datetime.utcnow().isoformat()
    last_run = db.query(func.max(IngestionJob.started_at)).scalar()
    last_success = (
        db.query(func.max(IngestionJob.completed_at))
        .filter(IngestionJob.status == "succeeded")
        .scalar()
    )
    error_count = (
        db.query(func.count(IngestionJob.id))
        .filter(IngestionJob.status == "failed")
        .scalar()
    )
    calendar_status = read_calendar_status()
    calendar_error = calendar_status.get("last_error")
    health = "attention" if error_count or calendar_error else "healthy"
    backup_status = {"status": "unknown", "last_success": None, "last_attempt": None, "last_restore": None}
    status_file = _status_path()
    if status_file.exists():
        with status_file.open("r", encoding="utf-8") as handle:
            backup_status = json.load(handle)

    return {
        "health": health,
        "db_encrypted": _db_encrypted(db),
        "briefing_last_run": None,
        "ingestion_last_run": last_run,
        "ingestion_last_success": last_success,
        "backup_last_status": backup_status,
        "calendar_status": calendar_status,
        "error_count": error_count,
        "updated_at": now,
    }


@router.get("/status/context-gaps")
def context_gaps(db: Session = Depends(get_db)) -> dict:
    now = datetime.utcnow()

    meeting_rows = (
        db.query(
            Meeting.id,
            Meeting.title,
            func.max(SourceRecord.captured_at).label("last_captured"),
        )
        .outerjoin(SourceRecord, SourceRecord.meeting_id == Meeting.id)
        .group_by(Meeting.id)
        .order_by(func.max(SourceRecord.captured_at).asc().nulls_first(), Meeting.starts_at.asc())
        .limit(5)
        .all()
    )

    meetings = []
    for meeting_id, title, last_captured in meeting_rows:
        days_since = None
        if last_captured:
            days_since = (now - last_captured).days
        meetings.append(
            {
                "id": meeting_id,
                "title": title,
                "last_updated": last_captured,
                "days_since": days_since,
            }
        )

    people_rows = (
        db.query(Person.id, Person.name, Person.last_interaction_at)
        .order_by(Person.last_interaction_at.asc().nulls_first(), Person.name.asc())
        .limit(5)
        .all()
    )
    people = []
    for person_id, name, last_interaction_at in people_rows:
        days_since = None
        if last_interaction_at:
            days_since = (now - last_interaction_at).days
        people.append(
            {
                "id": person_id,
                "name": name,
                "last_updated": last_interaction_at,
                "days_since": days_since,
            }
        )

    return {"updated_at": now.isoformat(), "meetings": meetings, "people": people}


@router.get("/status/relationship-signals")
def relationship_signals(db: Session = Depends(get_db)) -> dict:
    now = datetime.utcnow()
    since = now - timedelta(days=30)
    people_rows = (
        db.query(Person.id, Person.name, Person.last_interaction_at)
        .order_by(Person.name.asc())
        .all()
    )

    counts = (
        db.query(MeetingParticipant.person_id, func.count(SourceRecord.id))
        .join(SourceRecord, SourceRecord.meeting_id == MeetingParticipant.meeting_id)
        .filter(SourceRecord.captured_at >= since)
        .group_by(MeetingParticipant.person_id)
        .all()
    )
    count_map = {person_id: count for person_id, count in counts}

    items = []
    for person_id, name, last_interaction_at in people_rows:
        days_since = None
        if last_interaction_at:
            days_since = (now - last_interaction_at).days
        items.append(
            {
                "id": person_id,
                "name": name,
                "last_updated": last_interaction_at,
                "days_since": days_since,
                "recent_context_count": count_map.get(person_id, 0),
            }
        )

    return {"updated_at": now.isoformat(), "since": since.isoformat(), "items": items}


@router.get("/status/relationship-trajectories")
def relationship_trajectories(db: Session = Depends(get_db)) -> dict:
    now = datetime.utcnow()
    recent_since = now - timedelta(days=30)
    prior_since = now - timedelta(days=60)

    people_rows = (
        db.query(Person.id, Person.name, Person.last_interaction_at)
        .order_by(Person.name.asc())
        .all()
    )

    recent_counts = (
        db.query(MeetingParticipant.person_id, func.count(SourceRecord.id))
        .join(SourceRecord, SourceRecord.meeting_id == MeetingParticipant.meeting_id)
        .filter(SourceRecord.captured_at >= recent_since)
        .group_by(MeetingParticipant.person_id)
        .all()
    )
    prior_counts = (
        db.query(MeetingParticipant.person_id, func.count(SourceRecord.id))
        .join(SourceRecord, SourceRecord.meeting_id == MeetingParticipant.meeting_id)
        .filter(SourceRecord.captured_at >= prior_since)
        .filter(SourceRecord.captured_at < recent_since)
        .group_by(MeetingParticipant.person_id)
        .all()
    )
    recent_map = {person_id: count for person_id, count in recent_counts}
    prior_map = {person_id: count for person_id, count in prior_counts}

    items = []
    for person_id, name, last_interaction_at in people_rows:
        recent_count = recent_map.get(person_id, 0)
        prior_count = prior_map.get(person_id, 0)
        if recent_count > prior_count:
            trajectory = "More present"
        elif recent_count < prior_count:
            trajectory = "Less present"
        else:
            trajectory = "Steady"
        items.append(
            {
                "id": person_id,
                "name": name,
                "last_updated": last_interaction_at,
                "recent_count": recent_count,
                "prior_count": prior_count,
                "trajectory": trajectory,
            }
        )

    return {
        "updated_at": now.isoformat(),
        "recent_since": recent_since.isoformat(),
        "prior_since": prior_since.isoformat(),
        "items": items,
    }


class StatusAction(BaseModel):
    action: str


@router.post("/status/actions")
def status_actions(request: StatusAction, db: Session = Depends(get_db)) -> dict:
    if request.action == "run_backup":
        result = create_backup()
        db.add(
            AuditLog(
                id=f"al_{uuid4().hex}",
                actor="system",
                action="run_backup",
                entity_type="backup",
                entity_id=result.get("path", "unknown"),
            )
        )
        db.commit()
        return {"queued": False, "result": result}
    return {"queued": False, "result": {"status": "ignored"}}
