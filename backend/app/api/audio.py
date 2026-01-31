from __future__ import annotations

from datetime import datetime
import json
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.ingestion_job import IngestionJob
from app.models.meeting import Meeting
from app.models.person import Person
from app.settings import get_data_dir

router = APIRouter(prefix="/api/audio", tags=["audio"])


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


@router.post("/recordings", status_code=status.HTTP_202_ACCEPTED)
async def create_audio_recording(
    meeting_id: str = Form(...),
    file: UploadFile = File(...),
    people_ids: str | None = Form(None),
    relevant_at: str | None = Form(None),
    commitment_relevant_by: str | None = Form(None),
    index_in_memory: bool | None = Form(None),
    db: Session = Depends(get_db),
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not file:
        raise HTTPException(status_code=400, detail="Audio file required")

    data_dir = get_data_dir()
    audio_dir = os.path.join(data_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[-1] or ".webm"
    job_id = f"j_{uuid4().hex}"
    filename = f"audio_{job_id}{ext}"
    path = os.path.join(audio_dir, filename)

    contents = await file.read()
    with open(path, "wb") as handle:
        handle.write(contents)

    people_json = None
    if people_ids:
        try:
            incoming = json.loads(people_ids)
        except json.JSONDecodeError:
            incoming = []
        if isinstance(incoming, list):
            cleaned = [pid for pid in incoming if isinstance(pid, str) and pid.strip()]
            if cleaned:
                existing = db.query(Person.id).filter(Person.id.in_(cleaned)).all()
                existing_ids = [pid for (pid,) in existing]
                if existing_ids:
                    people_json = json.dumps(existing_ids)

    job = IngestionJob(
        id=job_id,
        meeting_id=meeting_id,
        payload=f"Audio recording captured ({filename}).",
        capture_type="audio",
        people_ids=people_json,
        relevant_at=_parse_iso(relevant_at),
        commitment_relevant_by=_parse_iso(commitment_relevant_by),
        index_in_memory=bool(index_in_memory) if index_in_memory is not None else False,
        media_path=path,
        status="queued",
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    return {"job_id": job_id}
