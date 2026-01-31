import base64
import io
import json
import zipfile
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Commitment, Meeting, Person, SourceRecord

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    meeting_ids: List[str] = []
    people_ids: List[str] = []
    start: str | None = None
    end: str | None = None
    format: str = "markdown"


def _filter_sources(db: Session, payload: ExportRequest):
    query = db.query(SourceRecord, Meeting).outerjoin(Meeting, Meeting.id == SourceRecord.meeting_id)
    if payload.meeting_ids:
        query = query.filter(SourceRecord.meeting_id.in_(payload.meeting_ids))
    if payload.start:
        query = query.filter(SourceRecord.captured_at >= datetime.fromisoformat(payload.start))
    if payload.end:
        query = query.filter(SourceRecord.captured_at <= datetime.fromisoformat(payload.end))
    return query.order_by(SourceRecord.captured_at.desc()).all()


@router.post("/preview")
def export_preview(payload: ExportRequest, db: Session = Depends(get_db)):
    rows = _filter_sources(db, payload)
    items = []
    for source, meeting in rows[:50]:
        items.append({
            "source_id": source.id,
            "meeting_title": meeting.title if meeting else None,
            "captured_at": source.captured_at.isoformat() if source.captured_at else None,
            "capture_type": source.capture_type,
            "excerpt": source.summary_text,
        })
    return {"count": len(rows), "items": items}


@router.post("/run")
def export_run(payload: ExportRequest, db: Session = Depends(get_db)):
    rows = _filter_sources(db, payload)
    if payload.format == "json":
        data = [
            {
                "source_id": source.id,
                "meeting_title": meeting.title if meeting else None,
                "captured_at": source.captured_at.isoformat() if source.captured_at else None,
                "capture_type": source.capture_type,
                "summary": source.summary_text,
            }
            for source, meeting in rows
        ]
        return {"format": "json", "content": data}

    lines = ["# Custos Export"]
    for source, meeting in rows:
        lines.append(f"## {meeting.title if meeting else 'Context'}")
        lines.append(f"- Captured: {source.captured_at}")
        lines.append(f"- Type: {source.capture_type}")
        if source.summary_text:
            lines.append(source.summary_text)
        lines.append("")
    return {"format": "markdown", "content": "\n".join(lines)}


@router.post("/encrypted")
def export_encrypted(payload: ExportRequest, password: str, db: Session = Depends(get_db)):
    export = export_run(payload, db)
    content = json.dumps(export).encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.setpassword(password.encode("utf-8"))
        zf.writestr("export.json", content)
    return {"filename": "custos-export.zip", "data": base64.b64encode(buffer.getvalue()).decode("utf-8")}


@router.get("/ics")
def export_ics(db: Session = Depends(get_db)):
    meetings = db.query(Meeting).order_by(Meeting.starts_at.asc()).all()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0"]
    for meeting in meetings:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{meeting.id}")
        if meeting.starts_at:
            lines.append(f"DTSTART:{meeting.starts_at.strftime('%Y%m%dT%H%M%SZ')}")
        if meeting.ends_at:
            lines.append(f"DTEND:{meeting.ends_at.strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"SUMMARY:{meeting.title}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return {"ics": "\n".join(lines)}


@router.post("/full")
def export_full(db: Session = Depends(get_db)):
    meetings = db.query(Meeting).all()
    people = db.query(Person).all()
    sources = db.query(SourceRecord).all()
    commitments = db.query(Commitment).all()
    data = {
        "meetings": [meeting.__dict__ for meeting in meetings],
        "people": [person.__dict__ for person in people],
        "sources": [source.__dict__ for source in sources],
        "commitments": [commitment.__dict__ for commitment in commitments],
    }
    return {"export": data}
