from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.ingestion_job import IngestionJob

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


class IngestionRequest(BaseModel):
    meeting_id: str
    capture_type: str
    payload: str


class IngestionResponse(BaseModel):
    job_id: str


class IngestionStatusResponse(BaseModel):
    id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None


@router.post("", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
def create_ingestion(request: IngestionRequest, db: Session = Depends(get_db)) -> IngestionResponse:
    if request.capture_type not in {"notes", "transcript"}:
        raise HTTPException(status_code=400, detail="Invalid capture_type")
    job_id = f"j_{uuid4().hex}"
    job = IngestionJob(
        id=job_id,
        meeting_id=request.meeting_id,
        payload=request.payload,
        capture_type=request.capture_type,
        status="queued",
    )
    db.add(job)
    db.commit()
    return IngestionResponse(job_id=job_id)


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
