from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.nas_sync_settings import NasSyncSettings
from app.ops.sync import run_sync, restore_from_sync

router = APIRouter(prefix="/api/sync", tags=["sync"])


class SyncSettingsPayload(BaseModel):
    mount_path: str
    enabled: bool = False


def _get_settings(db: Session) -> NasSyncSettings:
    settings = db.query(NasSyncSettings).first()
    if not settings:
        settings = NasSyncSettings(id=f"sync_{uuid4().hex}", mount_path="", enabled=False)
        db.add(settings)
        db.commit()
    return settings


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)) -> dict:
    settings = _get_settings(db)
    return {
        "mount_path": settings.mount_path,
        "enabled": settings.enabled,
        "last_sync_at": settings.last_sync_at,
        "last_error": settings.last_error,
    }


@router.put("/settings")
def set_settings(payload: SyncSettingsPayload, db: Session = Depends(get_db)) -> dict:
    settings = _get_settings(db)
    settings.mount_path = payload.mount_path
    settings.enabled = payload.enabled
    settings.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "saved"}


@router.post("/run")
def run_sync_now(db: Session = Depends(get_db)) -> dict:
    settings = _get_settings(db)
    if not settings.enabled or not settings.mount_path:
        raise HTTPException(status_code=400, detail="sync_not_configured")
    result = run_sync(settings.mount_path)
    settings.last_sync_at = datetime.utcnow()
    settings.last_error = result.get("error")
    db.commit()
    return result


@router.post("/restore")
def restore_sync(db: Session = Depends(get_db)) -> dict:
    settings = _get_settings(db)
    if not settings.mount_path:
        raise HTTPException(status_code=400, detail="sync_not_configured")
    result = restore_from_sync(settings.mount_path)
    settings.last_error = result.get("error")
    db.commit()
    return result
