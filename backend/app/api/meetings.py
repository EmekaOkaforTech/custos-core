from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.meeting import Meeting

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


class MeetingCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    starts_at: datetime | None = None


class MeetingUpdateRequest(BaseModel):
    title: str = Field(min_length=1)


class MeetingResponse(BaseModel):
    id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    source: str | None = None


@router.post("", response_model=MeetingResponse)
def create_meeting(payload: MeetingCreateRequest, db: Session = Depends(get_db)) -> MeetingResponse:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="title must not be blank")
    starts_at = payload.starts_at or (datetime.utcnow() + timedelta(hours=1))
    ends_at = starts_at + timedelta(hours=1)
    meeting = Meeting(
        id=f"m_{uuid4().hex}",
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
        source="manual",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        starts_at=meeting.starts_at,
        ends_at=meeting.ends_at,
        source=meeting.source,
    )


@router.patch("/{meeting_id}", response_model=MeetingResponse)
def update_meeting(meeting_id: str, payload: MeetingUpdateRequest, db: Session = Depends(get_db)) -> MeetingResponse:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="title must not be blank")
    meeting.title = title
    db.commit()
    db.refresh(meeting)
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        starts_at=meeting.starts_at,
        ends_at=meeting.ends_at,
        source=meeting.source,
    )


@router.get("")
def list_meetings(
    range: Literal["today", "upcoming"] = Query("upcoming"),
    db: Session = Depends(get_db),
) -> dict:
    now = datetime.utcnow()
    if range == "today":
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)
        meetings = (
            db.query(Meeting)
            .filter(Meeting.starts_at >= start, Meeting.starts_at < end)
            .order_by(Meeting.starts_at.asc())
            .all()
        )
    elif range == "upcoming":
        meetings = (
            db.query(Meeting)
            .filter(Meeting.starts_at >= now)
            .order_by(Meeting.starts_at.asc())
            .all()
        )
    else:
        raise HTTPException(status_code=400, detail="range must be today or upcoming")

    return {
        "range": range,
        "meetings": [
            {
                "id": meeting.id,
                "title": meeting.title,
                "starts_at": meeting.starts_at,
                "ends_at": meeting.ends_at,
                "source": meeting.source,
            }
            for meeting in meetings
        ],
        "updated_at": now.isoformat(),
    }
