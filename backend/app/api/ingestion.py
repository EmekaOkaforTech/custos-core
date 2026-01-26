from datetime import datetime, timezone
import hashlib
from uuid import uuid4
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
import json

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.ingestion_job import IngestionJob
from app.models.meeting import Meeting
from app.models.person import Person

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


class IngestionRequest(BaseModel):
    meeting_id: str
    capture_type: str
    payload: str
    people_ids: list[str] | None = None
    relevant_at: datetime | None = None
    commitment_relevant_by: datetime | None = None
    index_in_memory: bool | None = None


class IngestionResponse(BaseModel):
    job_id: str


class IngestionStatusResponse(BaseModel):
    id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None


class RecentCaptureMeeting(BaseModel):
    id: str
    title: str
    starts_at: datetime | None


class RecentCapturePerson(BaseModel):
    id: str
    name: str
    type: str


class RecentCapture(BaseModel):
    id: str
    source_id: str | None
    capture_type: str
    payload: str
    captured_at: datetime
    meeting: RecentCaptureMeeting
    people: list[RecentCapturePerson]

DEDUP_WINDOW_SECONDS = 120


def _normalize_payload(payload: str | None) -> str:
    if not payload:
        return ""
    return " ".join(payload.strip().split()).lower()


def _dedupe_key(meeting_id: str, capture_type: str, payload: str, people_ids: str | None, relevant_at: datetime | None) -> str:
    parts = [
        meeting_id,
        capture_type,
        payload,
        (people_ids or "").strip(),
        relevant_at.isoformat() if relevant_at else "",
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_relevant_at(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


@router.post("", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
def create_ingestion(request: IngestionRequest, db: Session = Depends(get_db)) -> IngestionResponse:
    if request.capture_type not in {"notes", "transcript", "decision", "follow-up", "reflection"}:
        raise HTTPException(status_code=400, detail="Invalid capture_type")
    meeting = db.get(Meeting, request.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    people_json = None
    if request.people_ids:
        people_ids = [pid.strip() for pid in request.people_ids if pid.strip()]
        if people_ids:
            existing = db.query(Person.id).filter(Person.id.in_(people_ids)).all()
            existing_ids = [pid for (pid,) in existing]
            if existing_ids:
                people_json = json.dumps(existing_ids)
    normalized_payload = _normalize_payload(request.payload)
    relevant_at = _normalize_relevant_at(request.relevant_at)
    index_in_memory = (
        request.index_in_memory
        if request.index_in_memory is not None
        else request.capture_type == "reflection"
    )
    dedupe_key = _dedupe_key(request.meeting_id, request.capture_type, normalized_payload, people_json, relevant_at)
    if normalized_payload:
        cutoff = datetime.utcnow() - timedelta(seconds=DEDUP_WINDOW_SECONDS)
        candidates = (
            db.query(IngestionJob)
            .filter(IngestionJob.meeting_id == request.meeting_id)
            .filter(IngestionJob.capture_type == request.capture_type)
            .filter(IngestionJob.created_at >= cutoff)
            .filter(IngestionJob.people_ids == people_json)
            .filter(IngestionJob.relevant_at == relevant_at)
            .filter(IngestionJob.dedupe_key == dedupe_key)
            .order_by(IngestionJob.created_at.desc())
            .all()
        )
        for candidate in candidates:
            if _normalize_payload(candidate.payload) == normalized_payload:
                return IngestionResponse(job_id=candidate.id)
    job_id = f"j_{uuid4().hex}"
    job = IngestionJob(
        id=job_id,
        meeting_id=request.meeting_id,
        payload=request.payload,
        capture_type=request.capture_type,
        people_ids=people_json,
        relevant_at=relevant_at,
        commitment_relevant_by=request.commitment_relevant_by,
        index_in_memory=index_in_memory,
        dedupe_key=dedupe_key,
        status="queued",
    )
    db.add(job)
    db.commit()
    return IngestionResponse(job_id=job_id)


@router.get("/recent", response_model=list[RecentCapture])
def get_recent_ingestion(limit: int = 5, db: Session = Depends(get_db)) -> list[RecentCapture]:
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    if limit > 20:
        raise HTTPException(status_code=400, detail="limit must be <= 20")
    jobs = (
        db.query(IngestionJob)
        .filter(IngestionJob.status == "succeeded")
        .filter((IngestionJob.error == None) | (IngestionJob.error != "deduped"))  # noqa: E711
        .order_by(IngestionJob.completed_at.desc(), IngestionJob.created_at.desc())
        .limit(limit)
        .all()
    )
    if not jobs:
        return []

    meeting_ids = {job.meeting_id for job in jobs}
    meetings = db.query(Meeting).filter(Meeting.id.in_(meeting_ids)).all()
    meeting_map = {meeting.id: meeting for meeting in meetings}

    people_ids = set()
    job_people = {}
    for job in jobs:
        if not job.people_ids:
            job_people[job.id] = []
            continue
        try:
            ids = [pid for pid in json.loads(job.people_ids) if pid]
        except json.JSONDecodeError:
            ids = []
        job_people[job.id] = ids
        people_ids.update(ids)

    people_map = {}
    if people_ids:
        people = db.query(Person).filter(Person.id.in_(people_ids)).all()
        people_map = {person.id: person for person in people}

    results: list[RecentCapture] = []
    for job in jobs:
        meeting = meeting_map.get(job.meeting_id)
        if not meeting:
            continue
        captured_at = job.completed_at or job.created_at
        people = [
            RecentCapturePerson(id=pid, name=people_map[pid].name, type=people_map[pid].type)
            for pid in job_people.get(job.id, [])
            if pid in people_map
        ]
        results.append(
            RecentCapture(
                id=job.id,
                source_id=job.source_id,
                capture_type=job.capture_type,
                payload=job.payload,
                captured_at=captured_at,
                meeting=RecentCaptureMeeting(
                    id=meeting.id,
                    title=meeting.title,
                    starts_at=meeting.starts_at,
                ),
                people=people,
            )
        )
    return results


@router.get("/decisions", response_model=list[RecentCapture])
def get_recent_decisions(
    days: int = 7,
    limit: int = 5,
    db: Session = Depends(get_db),
) -> list[RecentCapture]:
    if days < 1 or days > 30:
        raise HTTPException(status_code=400, detail="days must be between 1 and 30")
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 20")
    cutoff = datetime.utcnow() - timedelta(days=days)
    jobs = (
        db.query(IngestionJob)
        .filter(IngestionJob.status == "succeeded")
        .filter(IngestionJob.capture_type == "decision")
        .filter((IngestionJob.error == None) | (IngestionJob.error != "deduped"))  # noqa: E711
        .filter(IngestionJob.created_at >= cutoff)
        .order_by(IngestionJob.completed_at.desc(), IngestionJob.created_at.desc())
        .limit(limit)
        .all()
    )
    if not jobs:
        return []

    meeting_ids = {job.meeting_id for job in jobs}
    meetings = db.query(Meeting).filter(Meeting.id.in_(meeting_ids)).all()
    meeting_map = {meeting.id: meeting for meeting in meetings}

    people_ids = set()
    job_people = {}
    for job in jobs:
        if not job.people_ids:
            job_people[job.id] = []
            continue
        try:
            ids = [pid for pid in json.loads(job.people_ids) if pid]
        except json.JSONDecodeError:
            ids = []
        job_people[job.id] = ids
        people_ids.update(ids)

    people_map = {}
    if people_ids:
        people = db.query(Person).filter(Person.id.in_(people_ids)).all()
        people_map = {person.id: person for person in people}

    results: list[RecentCapture] = []
    for job in jobs:
        meeting = meeting_map.get(job.meeting_id)
        if not meeting:
            continue
        captured_at = job.completed_at or job.created_at
        people = [
            RecentCapturePerson(id=pid, name=people_map[pid].name, type=people_map[pid].type)
            for pid in job_people.get(job.id, [])
            if pid in people_map
        ]
        results.append(
            RecentCapture(
                id=job.id,
                source_id=job.source_id,
                capture_type=job.capture_type,
                payload=job.payload,
                captured_at=captured_at,
                meeting=RecentCaptureMeeting(
                    id=meeting.id,
                    title=meeting.title,
                    starts_at=meeting.starts_at,
                ),
                people=people,
            )
        )
    return results


@router.get("/{job_id}", response_model=IngestionStatusResponse)
def get_ingestion(job_id: str, db: Session = Depends(get_db)) -> IngestionStatusResponse:
    job = db.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return IngestionStatusResponse(
        id=job.id,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@router.post("/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_ingestion(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    job.status = "queued"
    job.error = None
    db.commit()
    return {"queued": True}
