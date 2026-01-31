"""
Briefings API endpoints for Custos Core.

Epic 33: Person-First Briefing Mode
- GET /api/briefings/by-person - Briefing organized by person
- Person priority ordering by commitments + recency

Epic 35: Professional Context Mode
- Session continuity card for client sessions
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.commitment import Commitment
from app.models.meeting import Meeting
from app.models.source_record import SourceRecord
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.email_message import EmailMessage

router = APIRouter(prefix="/api/briefings", tags=["briefings"])

STALE_DAYS = 14


def _status_for(last_source_at: datetime | None, now: datetime) -> str:
    if not last_source_at:
        return "missing"
    if now - last_source_at > timedelta(days=STALE_DAYS):
        return "stale"
    return "ok"


def _apply_visibility(query, user_id: str | None):
    if not user_id:
        return query
    return query.filter(
        (SourceRecord.visibility == "shared") | (SourceRecord.owner_id == user_id)
    )


@router.get("/today")
def get_today_briefings(
    db: Session = Depends(get_db),
    cached: bool = Query(False),
    offline: bool = Query(False),
    cached_at: datetime | None = Query(None),
    calendar_source: str | None = Query(None),  # Story 37.5: Filter by calendar
    user_id: str | None = Query(None),
) -> dict:
    now = cached_at or datetime.utcnow()
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)

    query = db.query(Meeting).filter(
        Meeting.starts_at >= start,
        Meeting.starts_at < end,
        Meeting.cancelled_at.is_(None),  # Exclude cancelled meetings (Story 37.2)
    )

    # Story 37.5: Filter by calendar source if specified
    if calendar_source:
        query = query.filter(Meeting.calendar_source_id == calendar_source)

    meetings = query.order_by(Meeting.starts_at.asc()).all()

    results = []
    for meeting in meetings:
        source = (
            _apply_visibility(db.query(SourceRecord)
            .filter(SourceRecord.meeting_id == meeting.id), user_id)
            .order_by(SourceRecord.captured_at.desc())
            .first()
        )
        last_source_at = source.captured_at if source else None
        status = _status_for(last_source_at, now)
        commitments_count = (
            _apply_visibility(db.query(func.count(Commitment.id))
            .join(SourceRecord, Commitment.source_id == SourceRecord.id)
            .filter(SourceRecord.meeting_id == meeting.id), user_id)
            .scalar()
        )
        results.append(
            {
                "id": meeting.id,
                "title": meeting.title,
                "starts_at": meeting.starts_at,
                "status": status,
                "last_source_at": last_source_at,
                "open_commitments": commitments_count or 0,
                "calendar_source_id": meeting.calendar_source_id,  # Story 37.5
            }
        )

    return {
        "date": start.date().isoformat(),
        "meetings": results,
        "updated_at": now.isoformat(),
        "cached": cached,
        "offline": offline,
    }


@router.get("/next")
def get_next_briefing(
    db: Session = Depends(get_db),
    cached: bool = Query(False),
    offline: bool = Query(False),
    cached_at: datetime | None = Query(None),
    calendar_source: str | None = Query(None),  # Story 37.5: Filter by calendar
    user_id: str | None = Query(None),
) -> dict:
    now = cached_at or datetime.utcnow()

    query = db.query(Meeting).filter(
        Meeting.starts_at >= now,
        Meeting.cancelled_at.is_(None),  # Exclude cancelled meetings (Story 37.2)
    )

    # Story 37.5: Filter by calendar source if specified
    if calendar_source:
        query = query.filter(Meeting.calendar_source_id == calendar_source)

    meeting = query.order_by(Meeting.starts_at.asc()).first()

    if not meeting:
        future_query = (
            db.query(SourceRecord, Meeting)
            .join(Meeting, SourceRecord.meeting_id == Meeting.id)
        )
        if user_id:
            future_query = future_query.filter((SourceRecord.visibility == "shared") | (SourceRecord.owner_id == user_id))
        future_relevant = (
            future_query
            .filter(SourceRecord.relevant_at != None)  # noqa: E711
            .filter(SourceRecord.relevant_at >= now)
            .filter(Meeting.cancelled_at.is_(None))  # Exclude cancelled meetings (Story 37.2)
            .order_by(SourceRecord.relevant_at.asc())
            .all()
        )
        future_items = []
        for source, meeting_item in future_relevant:
            future_items.append(
                {
                    "source_id": source.id,
                    "capture_type": source.capture_type,
                    "captured_at": source.captured_at,
                    "relevant_at": source.relevant_at,
                    "meeting": {
                        "id": meeting_item.id,
                        "title": meeting_item.title,
                        "starts_at": meeting_item.starts_at,
                    },
                }
            )
        return {
            "meeting": None,
            "cards": [],
            "commitments": [],
            "future_relevant": future_items,
            "updated_at": now.isoformat(),
            "cached": cached,
            "offline": offline,
        }

    source_query = (
        db.query(SourceRecord)
        .filter(SourceRecord.meeting_id == meeting.id)
    )
    if user_id:
        source_query = source_query.filter((SourceRecord.visibility == "shared") | (SourceRecord.owner_id == user_id))
    source = (
        source_query
        .order_by(SourceRecord.captured_at.desc())
        .first()
    )

    last_source_at = source.captured_at if source else None
    status = _status_for(last_source_at, now)

    if source:
        if source.capture_type == "email":
            thread_count = (
                db.query(func.count(EmailMessage.id))
                .filter(EmailMessage.meeting_id == meeting.id)
                .scalar()
            )
            summary = f"{thread_count or 0} emails in this thread."
        else:
            summary = f"Context captured via {source.capture_type}."
        source_meta = {
            "id": source.id,
            "captured_at": source.captured_at,
            "capture_type": source.capture_type,
            "uri": source.uri,
        }
        rule_meta = {"id": "source_capture", "type": source.capture_type}
    else:
        summary = "No recent context available."
        source_meta = None
        rule_meta = {"id": "no_source", "type": "absence"}

    commitments = (
        db.query(Commitment)
        .join(SourceRecord, Commitment.source_id == SourceRecord.id)
        .filter(SourceRecord.meeting_id == meeting.id)
        .order_by(Commitment.due_at.asc().nulls_last(), Commitment.created_at.asc())
        .all()
    )

    people = (
        db.query(Person)
        .join(MeetingParticipant, MeetingParticipant.person_id == Person.id)
        .filter(MeetingParticipant.meeting_id == meeting.id)
        .order_by(Person.name.asc())
        .all()
    )
    people_meta = [{"id": person.id, "name": person.name, "type": person.type} for person in people]

    return {
        "meeting": {
            "id": meeting.id,
            "title": meeting.title,
            "starts_at": meeting.starts_at,
        },
        "cards": [
            {
                "summary": summary,
                "status": status,
                "last_source_at": last_source_at,
                "source": source_meta,
                "reason": {
                    "meeting": {
                        "id": meeting.id,
                        "title": meeting.title,
                        "starts_at": meeting.starts_at,
                    },
                    "source": source_meta,
                    "people": people_meta,
                    "rule": rule_meta,
                },
            }
        ],
        "commitments": [
            {
                "id": item.id,
                "text": item.text,
                "acknowledged": item.acknowledged,
                "source_id": item.source_id,
                "rule_id": item.rule_id,
                "due_at": item.due_at,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in commitments
        ],
        "future_relevant": [],
        "updated_at": now.isoformat(),
        "cached": cached,
        "offline": offline,
    }


@router.get("/by-person")
def get_briefings_by_person(
    db: Session = Depends(get_db),
    cached: bool = Query(False),
    offline: bool = Query(False),
    cached_at: datetime | None = Query(None),
) -> dict:
    """
    Get briefing organized by person instead of by time (Epic 33).

    Returns people ordered by:
    1. Open commitments count (descending)
    2. Last interaction recency (descending)

    Each person includes:
    - Open commitments
    - Recent notes excerpt
    - Last interaction date
    - Session continuity (for Professional mode - Epic 35)
    """
    now = cached_at or datetime.utcnow()

    # Get all people with their metrics
    people = db.query(Person).order_by(Person.name.asc()).all()

    person_briefings = []

    for person in people:
        # Get open commitments for this person (from meeting-based sources)
        meeting_commits = (
            db.query(Commitment)
            .join(SourceRecord, Commitment.source_id == SourceRecord.id)
            .join(MeetingParticipant, MeetingParticipant.meeting_id == SourceRecord.meeting_id)
            .filter(
                MeetingParticipant.person_id == person.id,
                Commitment.acknowledged.is_(False),
            )
            .all()
        )

        # Get open commitments from direct sources
        direct_commits = (
            db.query(Commitment)
            .join(SourceRecord, Commitment.source_id == SourceRecord.id)
            .filter(
                SourceRecord.person_id == person.id,
                SourceRecord.meeting_id.is_(None),
                Commitment.acknowledged.is_(False),
            )
            .all()
        )

        all_commitments = meeting_commits + direct_commits

        # Get recent direct notes (last 3)
        recent_notes = (
            db.query(SourceRecord)
            .filter(
                SourceRecord.person_id == person.id,
                SourceRecord.meeting_id.is_(None),
            )
            .order_by(desc(SourceRecord.captured_at))
            .limit(3)
            .all()
        )

        # Get last meeting with this person for session continuity (Epic 35)
        last_meeting = (
            db.query(Meeting)
            .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
            .filter(
                MeetingParticipant.person_id == person.id,
                Meeting.starts_at < now,
                Meeting.cancelled_at.is_(None),  # Exclude cancelled meetings (Story 37.2)
            )
            .order_by(desc(Meeting.starts_at))
            .first()
        )

        # Get next upcoming meeting with this person
        next_meeting = (
            db.query(Meeting)
            .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
            .filter(
                MeetingParticipant.person_id == person.id,
                Meeting.starts_at >= now,
                Meeting.cancelled_at.is_(None),  # Exclude cancelled meetings (Story 37.2)
            )
            .order_by(Meeting.starts_at.asc())
            .first()
        )

        # Build session continuity card (Epic 35)
        session_continuity = None
        if last_meeting:
            last_session_source = (
                db.query(SourceRecord)
                .filter(SourceRecord.meeting_id == last_meeting.id)
                .order_by(desc(SourceRecord.captured_at))
                .first()
            )
            session_continuity = {
                "last_session_date": last_meeting.starts_at,
                "last_session_title": last_meeting.title,
                "has_notes": last_session_source is not None,
                "open_action_items": len(all_commitments),
            }

        person_briefings.append({
            "person": {
                "id": person.id,
                "name": person.name,
                "type": person.type,
                "role": person.role,
                "last_interaction_at": person.last_interaction_at,
            },
            "open_commitments": [
                {
                    "id": c.id,
                    "text": c.text,
                    "source_id": c.source_id,
                    "due_at": c.due_at,
                }
                for c in all_commitments
            ],
            "recent_notes": [
                {
                    "id": s.id,
                    "capture_type": s.capture_type,
                    "captured_at": s.captured_at,
                }
                for s in recent_notes
            ],
            "next_meeting": {
                "id": next_meeting.id,
                "title": next_meeting.title,
                "starts_at": next_meeting.starts_at,
            } if next_meeting else None,
            "session_continuity": session_continuity,
            "_sort_commitments": len(all_commitments),
            "_sort_recency": person.last_interaction_at or datetime.min,
        })

    # Sort by: (1) open commitments desc, (2) last interaction desc
    person_briefings.sort(
        key=lambda x: (-x["_sort_commitments"], x["_sort_recency"]),
        reverse=False,
    )
    person_briefings.sort(
        key=lambda x: x["_sort_recency"],
        reverse=True,
    )
    person_briefings.sort(
        key=lambda x: x["_sort_commitments"],
        reverse=True,
    )

    # Remove sort keys from response
    for pb in person_briefings:
        del pb["_sort_commitments"]
        del pb["_sort_recency"]

    return {
        "people": person_briefings,
        "updated_at": now.isoformat(),
        "cached": cached,
        "offline": offline,
    }
