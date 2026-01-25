from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.calendar.ingest import ingest_calendar
from app.calendar.status import mark_attempt
from app.db import get_db
from app.models.calendar_connection import CalendarConnection
from app.calendar.demo_provider import DemoCalendarProvider

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class CalendarConnectionRequest(BaseModel):
    provider: str = Field(min_length=1)
    scopes: list[str]
    token: str = Field(min_length=1)
    enabled: bool = True


class CalendarConnectionResponse(BaseModel):
    connected: bool
    provider: str | None = None
    scopes: list[str] = []
    enabled: bool = False
    updated_at: datetime | None = None


class CalendarPreviewItem(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime
    attendee_count: int


@router.post("/connection", response_model=CalendarConnectionResponse)
def set_connection(payload: CalendarConnectionRequest, db: Session = Depends(get_db)) -> CalendarConnectionResponse:
    provider = payload.provider.strip()
    token = payload.token.strip()
    scopes = [scope.strip() for scope in payload.scopes if scope.strip()]
    if provider not in {"demo", "local"}:
        raise HTTPException(status_code=422, detail="provider must be demo or local")
    if not token:
        raise HTTPException(status_code=422, detail="token must not be blank")
    if not scopes:
        raise HTTPException(status_code=422, detail="scopes must not be empty")

    scopes_json = json.dumps(scopes)
    existing = db.query(CalendarConnection).first()
    if existing:
        existing.provider = provider
        existing.scopes = scopes_json
        existing.token = token
        existing.enabled = payload.enabled
        db.add(existing)
        connection = existing
    else:
        connection = CalendarConnection(
            id=f"cal_{uuid4().hex}",
            provider=provider,
            scopes=scopes_json,
            token=token,
            enabled=payload.enabled,
        )
        db.add(connection)
    db.commit()
    db.refresh(connection)
    mark_attempt(enabled=payload.enabled)
    return CalendarConnectionResponse(
        connected=True,
        provider=connection.provider,
        scopes=scopes,
        enabled=connection.enabled,
        updated_at=connection.updated_at,
    )


@router.get("/connection", response_model=CalendarConnectionResponse)
def get_connection(db: Session = Depends(get_db)) -> CalendarConnectionResponse:
    connection = db.query(CalendarConnection).first()
    if not connection:
        return CalendarConnectionResponse(connected=False)
    try:
        scopes = json.loads(connection.scopes)
    except json.JSONDecodeError:
        scopes = []
    return CalendarConnectionResponse(
        connected=True,
        provider=connection.provider,
        scopes=scopes,
        enabled=connection.enabled,
        updated_at=connection.updated_at,
    )


@router.get("/preview")
def preview_calendar(
    range: str = Query("upcoming"),
    db: Session = Depends(get_db),
) -> dict:
    connection = db.query(CalendarConnection).first()
    if not connection:
        raise HTTPException(status_code=400, detail="calendar connection not configured")
    if not connection.enabled:
        raise HTTPException(status_code=400, detail="calendar connection disabled")
    provider = connection.provider
    if provider == "demo":
        calendar_provider = DemoCalendarProvider()
    else:
        raise HTTPException(status_code=400, detail="calendar provider not available")

    now = datetime.utcnow()
    if range == "today":
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)
    elif range == "upcoming":
        start = now
        end = now + timedelta(days=7)
    else:
        raise HTTPException(status_code=422, detail="range must be today or upcoming")

    events = calendar_provider.list_events(start, end)
    preview = []
    for event in events:
        attendees = calendar_provider.list_attendees(event.event_id)
        preview.append(
            CalendarPreviewItem(
                title=event.title,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                attendee_count=len(attendees),
            ).model_dump()
        )

    return {"range": range, "events": preview, "updated_at": now.isoformat()}


@router.post("/ingest")
def ingest_calendar_now(db: Session = Depends(get_db)) -> dict:
    connection = db.query(CalendarConnection).first()
    if not connection:
        raise HTTPException(status_code=400, detail="calendar connection not configured")
    if not connection.enabled:
        raise HTTPException(status_code=400, detail="calendar connection disabled")
    if connection.provider == "demo":
        provider = DemoCalendarProvider()
    else:
        raise HTTPException(status_code=400, detail="calendar provider not available")

    result = ingest_calendar(provider, db)
    return {"status": result.get("status"), "events": result.get("events", 0)}
