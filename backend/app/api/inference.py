from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.network_settings import NetworkSettings
from app.models.inference_task import InferenceTask
from app.ops.inference_queue import enqueue_task, run_once

router = APIRouter(prefix="/api/inference", tags=["inference"])


class InferenceSettingsPayload(BaseModel):
    inference_url: HttpUrl | None = None
    inference_enabled: bool = False


class InferenceQueueRequest(BaseModel):
    task_type: str
    payload: str | None = None
    priority: int | None = None


class InferenceQueueResponse(BaseModel):
    id: str
    task_type: str
    payload: str | None
    priority: int
    status: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


def _get_settings(db: Session) -> NetworkSettings:
    settings = db.query(NetworkSettings).first()
    if not settings:
        settings = NetworkSettings()
        db.add(settings)
        db.commit()
    return settings


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)) -> dict:
    settings = _get_settings(db)
    return {
        "inference_url": settings.inference_url,
        "inference_enabled": settings.inference_enabled,
        "inference_last_checked": settings.inference_last_checked,
        "inference_status": settings.inference_status,
    }


@router.put("/settings")
def set_settings(payload: InferenceSettingsPayload, db: Session = Depends(get_db)) -> dict:
    settings = _get_settings(db)
    settings.inference_url = str(payload.inference_url) if payload.inference_url else None
    settings.inference_enabled = payload.inference_enabled
    db.commit()
    return {
        "inference_url": settings.inference_url,
        "inference_enabled": settings.inference_enabled,
    }


@router.get("/status")
def check_status(db: Session = Depends(get_db)) -> dict:
    settings = _get_settings(db)
    url = settings.inference_url
    status = "disabled"
    if settings.inference_enabled and url:
        try:
            response = httpx.get(f"{url.rstrip('/')}/health", timeout=2)
            status = "healthy" if response.status_code == 200 else "unavailable"
        except Exception:
            status = "unavailable"
    settings.inference_status = status
    settings.inference_last_checked = datetime.utcnow()
    db.commit()
    return {
        "inference_url": url,
        "inference_enabled": settings.inference_enabled,
        "inference_status": status,
        "inference_last_checked": settings.inference_last_checked,
    }


@router.post("/queue", response_model=InferenceQueueResponse)
def queue_task(payload: InferenceQueueRequest, db: Session = Depends(get_db)) -> InferenceQueueResponse:
    if not payload.task_type.strip():
        raise HTTPException(status_code=422, detail="task_type must not be blank")
    priority = payload.priority if payload.priority is not None else (10 if payload.task_type == "voice" else 0)
    task = enqueue_task(payload.task_type, payload.payload, priority)
    return InferenceQueueResponse(
        id=task.id,
        task_type=task.task_type,
        payload=task.payload,
        priority=task.priority,
        status=task.status,
        error=task.error,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


@router.get("/queue", response_model=list[InferenceQueueResponse])
def list_queue(limit: int = 20, db: Session = Depends(get_db)) -> list[InferenceQueueResponse]:
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50")
    tasks = (
        db.query(InferenceTask)
        .order_by(InferenceTask.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        InferenceQueueResponse(
            id=task.id,
            task_type=task.task_type,
            payload=task.payload,
            priority=task.priority,
            status=task.status,
            error=task.error,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )
        for task in tasks
    ]


@router.post("/queue/run")
def run_queue_once() -> dict:
    return run_once()
