from datetime import datetime
from uuid import uuid4

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.audit_log import AuditLog
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
