import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.summarization_settings import SummarizationSettings
from app.models.source_record import SourceRecord
from app.models.ingestion_job import IngestionJob
from app.ops.inference_queue import enqueue_task

router = APIRouter(prefix='/summarization', tags=['summarization'])


class SummarizationSettingsOut(BaseModel):
    enabled: bool
    provider: str | None = None
    model: str | None = None
    max_input_tokens: int | None = None

    class Config:
        from_attributes = True


class SummarizationSettingsIn(BaseModel):
    enabled: bool
    provider: str | None = None
    model: str | None = None
    max_input_tokens: int | None = None


class SummarizationTaskResponse(BaseModel):
    task_id: str


def _get_or_create_settings(db: Session) -> SummarizationSettings:
    settings = db.query(SummarizationSettings).first()
    if settings:
        return settings
    settings = SummarizationSettings(
        enabled=False,
        provider='hailo',
        model='phi-3-mini',
        max_input_tokens=2000,
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.get('/settings', response_model=SummarizationSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    settings = _get_or_create_settings(db)
    return settings


@router.post('/settings', response_model=SummarizationSettingsOut)
def update_settings(payload: SummarizationSettingsIn, db: Session = Depends(get_db)):
    settings = _get_or_create_settings(db)
    settings.enabled = payload.enabled
    settings.provider = payload.provider
    settings.model = payload.model
    settings.max_input_tokens = payload.max_input_tokens
    db.commit()
    db.refresh(settings)
    return settings


@router.post('/run/{source_id}', response_model=SummarizationTaskResponse)
def run_summary(source_id: str, db: Session = Depends(get_db)):
    settings = _get_or_create_settings(db)
    if not settings.enabled:
        raise HTTPException(status_code=400, detail='Summarization disabled')
    source = db.query(SourceRecord).filter(SourceRecord.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail='Source not found')
    job = (
        db.query(IngestionJob)
        .filter(IngestionJob.source_id == source_id)
        .order_by(IngestionJob.completed_at.desc(), IngestionJob.created_at.desc())
        .first()
    )
    if not job or not job.payload:
        raise HTTPException(status_code=400, detail='Source has no payload to summarize')
    payload = {
        'source_id': source_id,
        'text': job.payload,
        'provider': settings.provider or 'hailo',
        'model': settings.model or 'phi-3-mini',
        'max_input_tokens': settings.max_input_tokens or 2000,
    }
    task = enqueue_task('summarize', json.dumps(payload), priority=1)
    return SummarizationTaskResponse(task_id=task.id)
