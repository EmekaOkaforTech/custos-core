from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.network_settings import NetworkSettings

router = APIRouter(prefix="/api/inference", tags=["inference"])


class InferenceSettingsPayload(BaseModel):
    inference_url: HttpUrl | None = None
    inference_enabled: bool = False


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
