from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import add_audit_entry, get_db
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

    old_title = meeting.title

    # Story 37.4: Track local override for calendar meetings
    if meeting.source == "calendar" and title != meeting.title:
        meeting.local_override = True
        # Store original calendar value if not already stored
        if meeting.calendar_title is None:
            meeting.calendar_title = meeting.title

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


@router.post("/{meeting_id}/force-refresh")
def force_refresh_meeting(meeting_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Force refresh a meeting from calendar, discarding local overrides.

    Story 37.4: Sync Conflict Resolution
    """
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.source != "calendar":
        raise HTTPException(status_code=400, detail="Can only force-refresh calendar meetings")

    if not meeting.local_override:
        return {"refreshed": False, "message": "No local override to clear"}

    # Restore calendar values
    old_title = meeting.title
    old_starts_at = meeting.starts_at
    old_ends_at = meeting.ends_at

    if meeting.calendar_title:
        meeting.title = meeting.calendar_title
    if meeting.calendar_starts_at:
        meeting.starts_at = meeting.calendar_starts_at
    if meeting.calendar_ends_at:
        meeting.ends_at = meeting.calendar_ends_at

    # Clear override tracking
    meeting.local_override = False
    meeting.calendar_title = None
    meeting.calendar_starts_at = None
    meeting.calendar_ends_at = None

    # Audit log
    add_audit_entry(
        db,
        action="meeting_force_refreshed",
        entity_type="Meeting",
        entity_id=meeting_id,
        payload={
            "old_title": old_title,
            "old_starts_at": old_starts_at.isoformat() if old_starts_at else None,
            "old_ends_at": old_ends_at.isoformat() if old_ends_at else None,
            "restored_title": meeting.title,
            "restored_starts_at": meeting.starts_at.isoformat() if meeting.starts_at else None,
            "restored_ends_at": meeting.ends_at.isoformat() if meeting.ends_at else None,
        },
    )

    db.commit()
    db.refresh(meeting)

    return {
        "refreshed": True,
        "meeting": {
            "id": meeting.id,
            "title": meeting.title,
            "starts_at": meeting.starts_at,
            "ends_at": meeting.ends_at,
        },
    }


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
