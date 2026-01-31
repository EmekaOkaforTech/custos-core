from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.network_settings import NetworkSettings
from app.network.services import scan_services

router = APIRouter(prefix="/api/network", tags=["network"])


class ManualService(BaseModel):
    type: str | None = None
    protocol: str | None = None
    host: str
    port: int
    name: str | None = None


class NetworkSettingsPayload(BaseModel):
    manual_services: list[ManualService] = Field(default_factory=list)
    discovery_enabled: bool = True
    scan_interval_minutes: int = 15


@router.get("/services")
def get_services(db: Session = Depends(get_db)) -> dict[str, Any]:
    result = scan_services(db)
    return result


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = db.query(NetworkSettings).first()
    if not settings:
        return NetworkSettingsPayload().model_dump()
    manual_services = []
    try:
        if settings.manual_services:
            manual_services = json.loads(settings.manual_services)
    except json.JSONDecodeError:
        manual_services = []
    return {
        "manual_services": manual_services,
        "discovery_enabled": settings.discovery_enabled,
        "scan_interval_minutes": settings.scan_interval_minutes,
        "last_scan_at": settings.last_scan_at,
    }


@router.put("/settings")
def set_settings(payload: NetworkSettingsPayload, db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = db.query(NetworkSettings).first()
    if not settings:
        settings = NetworkSettings()
        db.add(settings)
    settings.discovery_enabled = payload.discovery_enabled
    settings.scan_interval_minutes = payload.scan_interval_minutes
    settings.manual_services = json.dumps([svc.model_dump() for svc in payload.manual_services])
    db.commit()
    return {
        "manual_services": [svc.model_dump() for svc in payload.manual_services],
        "discovery_enabled": settings.discovery_enabled,
        "scan_interval_minutes": settings.scan_interval_minutes,
    }
