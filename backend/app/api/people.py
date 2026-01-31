"""
People API endpoints for Custos Core.

Epic 32: Person Profile Enrichment
- Person notes (direct capture)
- Person role/relationship field
- Person tags (lightweight)
- Person profile view

Epic 33: Person-First Briefing Mode (supported via list endpoint)
Epic 34/35: Care/Professional modes (capture types supported)
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db import add_audit_entry, get_db
from app.models.commitment import Commitment
from app.models.ingestion_job import IngestionJob
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.person_tag import PersonTag
from app.models.risk_flag import RiskFlag
from app.models.source_record import SourceRecord
from app.utils.datetime import utcnow

router = APIRouter(prefix="/api/people", tags=["people"])


# ============================================================================
# Request/Response Models
# ============================================================================

class PersonCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)


class PersonCreateResponse(BaseModel):
    id: str
    name: str
    type: str
    created: bool


class PersonUpdateRequest(BaseModel):
    type: str | None = None
    role: str | None = None


class PersonResponse(BaseModel):
    id: str
    name: str
    type: str
    role: str | None
    last_interaction_at: str | None


class TagRequest(BaseModel):
    tag: str = Field(min_length=1)


class TagResponse(BaseModel):
    id: str
    person_id: str
    tag: str


class PersonNoteRequest(BaseModel):
    capture_type: str = "notes"
    payload: str = Field(min_length=1)


class PersonNoteResponse(BaseModel):
    job_id: str


class SourceSummary(BaseModel):
    id: str
    captured_at: str
    capture_type: str
    source_type: str


class TimelineSummary(BaseModel):
    total_entries: int
    direct_count: int
    meeting_count: int


class PersonProfileResponse(BaseModel):
    id: str
    name: str
    type: str
    role: str | None
    tags: list[str]
    last_interaction_at: str | None
    recent_sources: list[SourceSummary]
    timeline_summary: TimelineSummary


# ============================================================================
# Potential Duplicates (Story 37.3)
# ============================================================================

@router.get("/duplicates")
def list_potential_duplicates(
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    List potential duplicate persons detected during calendar sync.

    Returns groups of persons that may be duplicates (same name, different email).
    Story 37.3: Attendee extraction and person matching.
    """
    # Find all persons with non-unique names (case-insensitive)
    name_counts = (
        db.query(
            func.lower(func.trim(Person.name)).label("normalized_name"),
            func.count(Person.id).label("cnt"),
        )
        .group_by(func.lower(func.trim(Person.name)))
        .having(func.count(Person.id) > 1)
        .subquery()
    )

    # Get all persons with duplicate names
    duplicates = (
        db.query(Person)
        .join(
            name_counts,
            func.lower(func.trim(Person.name)) == name_counts.c.normalized_name,
        )
        .order_by(Person.name, Person.created_at)
        .all()
    )

    # Group by normalized name
    groups: dict[str, list[dict]] = {}
    for person in duplicates:
        normalized = person.name.strip().lower()
        if normalized not in groups:
            groups[normalized] = []
        groups[normalized].append({
            "id": person.id,
            "name": person.name,
            "email": person.email,
            "type": person.type,
            "role": person.role,
            "created_at": person.created_at.isoformat() if person.created_at else None,
        })

    # Convert to list of groups
    result = []
    for name, persons in groups.items():
        result.append({
            "normalized_name": name,
            "persons": persons,
            "count": len(persons),
        })

    # Sort by count descending (most duplicates first)
    result.sort(key=lambda x: -x["count"])

    return result


# ============================================================================
# List People (with filters for role/tag)
# ============================================================================

@router.get("")
def list_people(
    role: str | None = None,
    tag: str | None = None,
    type: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    List all people with optional filters.

    Query params:
    - role: Filter by role (case-insensitive substring match)
    - tag: Filter by tag (case-insensitive exact match)
    - type: Filter by type (person or org, case-insensitive exact match)

    Returns enriched data for Epic 32-35 including:
    - role, tags, latest_source_at, open_commitments, risk_flags_count
    - last_observation_at (for Care mode)
    """
    # Get latest capture from meeting-based sources
    meeting_capture = (
        db.query(
            MeetingParticipant.person_id.label("person_id"),
            func.max(SourceRecord.captured_at).label("max_captured"),
        )
        .join(SourceRecord, SourceRecord.meeting_id == MeetingParticipant.meeting_id)
        .group_by(MeetingParticipant.person_id)
        .subquery()
    )

    # Get latest capture from direct sources
    direct_capture = (
        db.query(
            SourceRecord.person_id.label("person_id"),
            func.max(SourceRecord.captured_at).label("max_captured"),
        )
        .filter(
            SourceRecord.person_id.isnot(None),
            SourceRecord.meeting_id.is_(None),
        )
        .group_by(SourceRecord.person_id)
        .subquery()
    )

    # Open commitments from meeting-based sources
    open_commitments = (
        db.query(
            MeetingParticipant.person_id.label("person_id"),
            func.count(func.distinct(Commitment.id)).label("open_commitments"),
        )
        .join(SourceRecord, SourceRecord.meeting_id == MeetingParticipant.meeting_id)
        .join(Commitment, Commitment.source_id == SourceRecord.id)
        .filter(Commitment.acknowledged.is_(False))
        .group_by(MeetingParticipant.person_id)
        .subquery()
    )

    # Open commitments from direct sources
    direct_commitments = (
        db.query(
            SourceRecord.person_id.label("person_id"),
            func.count(func.distinct(Commitment.id)).label("open_commitments"),
        )
        .join(Commitment, Commitment.source_id == SourceRecord.id)
        .filter(
            Commitment.acknowledged.is_(False),
            SourceRecord.person_id.isnot(None),
            SourceRecord.meeting_id.is_(None),
        )
        .group_by(SourceRecord.person_id)
        .subquery()
    )

    # Risk flags from meeting-based sources
    risk_flags = (
        db.query(
            MeetingParticipant.person_id.label("person_id"),
            func.count(func.distinct(RiskFlag.id)).label("risk_flags_count"),
        )
        .join(SourceRecord, SourceRecord.meeting_id == MeetingParticipant.meeting_id)
        .join(RiskFlag, RiskFlag.source_id == SourceRecord.id)
        .group_by(MeetingParticipant.person_id)
        .subquery()
    )

    # Risk flags from direct sources
    direct_risk_flags = (
        db.query(
            SourceRecord.person_id.label("person_id"),
            func.count(func.distinct(RiskFlag.id)).label("risk_flags_count"),
        )
        .join(RiskFlag, RiskFlag.source_id == SourceRecord.id)
        .filter(
            SourceRecord.person_id.isnot(None),
            SourceRecord.meeting_id.is_(None),
        )
        .group_by(SourceRecord.person_id)
        .subquery()
    )

    query = (
        db.query(
            Person,
            meeting_capture.c.max_captured,
            direct_capture.c.max_captured,
            open_commitments.c.open_commitments,
            direct_commitments.c.open_commitments,
            risk_flags.c.risk_flags_count,
            direct_risk_flags.c.risk_flags_count,
        )
        .outerjoin(meeting_capture, meeting_capture.c.person_id == Person.id)
        .outerjoin(direct_capture, direct_capture.c.person_id == Person.id)
        .outerjoin(open_commitments, open_commitments.c.person_id == Person.id)
        .outerjoin(direct_commitments, direct_commitments.c.person_id == Person.id)
        .outerjoin(risk_flags, risk_flags.c.person_id == Person.id)
        .outerjoin(direct_risk_flags, direct_risk_flags.c.person_id == Person.id)
    )

    # Apply role filter (case-insensitive substring match)
    if role:
        query = query.filter(func.lower(Person.role).contains(role.lower()))

    # Apply type filter (case-insensitive exact match)
    if type:
        query = query.filter(func.lower(Person.type) == type.lower())

    # Apply tag filter (case-insensitive exact match)
    if tag:
        tag_subquery = (
            db.query(PersonTag.person_id)
            .filter(func.lower(PersonTag.tag) == tag.lower())
            .subquery()
        )
        query = query.filter(Person.id.in_(db.query(tag_subquery.c.person_id)))

    rows = query.order_by(Person.name.asc()).all()

    # Build tag lookup map
    all_person_ids = [row[0].id for row in rows]
    tags_query = (
        db.query(PersonTag.person_id, PersonTag.tag)
        .filter(PersonTag.person_id.in_(all_person_ids))
        .all()
    ) if all_person_ids else []

    person_tags: dict[str, list[str]] = {}
    for person_id, tag_value in tags_query:
        if person_id not in person_tags:
            person_tags[person_id] = []
        person_tags[person_id].append(tag_value)

    # Build observation lookup for Care mode
    observation_query = (
        db.query(
            SourceRecord.person_id,
            func.max(SourceRecord.captured_at).label("last_observation_at"),
        )
        .filter(
            SourceRecord.person_id.in_(all_person_ids),
            SourceRecord.capture_type == "observation",
        )
        .group_by(SourceRecord.person_id)
        .all()
    ) if all_person_ids else []

    person_observations: dict[str, any] = {}
    for person_id, last_obs_at in observation_query:
        person_observations[person_id] = last_obs_at

    response = []
    for (
        person,
        meeting_captured,
        direct_captured,
        meeting_commits,
        direct_commits,
        meeting_flags,
        direct_flags,
    ) in rows:
        # Determine latest source timestamp
        latest_source_at = None
        if meeting_captured and direct_captured:
            latest_source_at = max(meeting_captured, direct_captured)
        elif meeting_captured:
            latest_source_at = meeting_captured
        elif direct_captured:
            latest_source_at = direct_captured

        response.append({
            "id": person.id,
            "name": person.name,
            "type": person.type,
            "role": person.role,
            "tags": sorted(person_tags.get(person.id, [])),
            "last_interaction_at": person.last_interaction_at,
            "latest_source_at": latest_source_at,
            "open_commitments": (meeting_commits or 0) + (direct_commits or 0),
            "risk_flags_count": (meeting_flags or 0) + (direct_flags or 0),
            "last_observation_at": person_observations.get(person.id),
        })

    return response


# ============================================================================
# Create Person
# ============================================================================

@router.post("", response_model=PersonCreateResponse)
def create_person(
    request: PersonCreateRequest,
    db: Session = Depends(get_db),
) -> PersonCreateResponse:
    """Create a new person or return existing if name matches."""
    name = request.name.strip()
    person_type = request.type.strip().lower()

    if not name:
        raise HTTPException(status_code=422, detail="name must not be blank")
    if person_type not in {"person", "org"}:
        raise HTTPException(status_code=422, detail="type must be person or org")

    existing = (
        db.query(Person)
        .filter(func.lower(Person.name) == name.lower())
        .first()
    )
    if existing:
        return PersonCreateResponse(
            id=existing.id,
            name=existing.name,
            type=existing.type,
            created=False,
        )

    now = utcnow()
    person = Person(
        id=f"p_{uuid4().hex}",
        name=name,
        type=person_type,
        role=None,
        last_interaction_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(person)

    add_audit_entry(
        db,
        action="person_created",
        entity_type="Person",
        entity_id=person.id,
        payload={"name": name, "type": person_type},
    )

    db.commit()

    return PersonCreateResponse(
        id=person.id,
        name=person.name,
        type=person.type,
        created=True,
    )


# ============================================================================
# Get Person Profile (Epic 32.4)
# ============================================================================

@router.get("/{person_id}", response_model=PersonProfileResponse)
def get_person_profile(
    person_id: str,
    db: Session = Depends(get_db),
) -> PersonProfileResponse:
    """Get detailed person profile with tags, recent sources, and timeline summary."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Get tags
    tags = (
        db.query(PersonTag.tag)
        .filter(PersonTag.person_id == person_id)
        .order_by(PersonTag.tag)
        .all()
    )
    tag_list = [t[0] for t in tags]

    # Get recent direct sources (limit 5)
    direct_sources = (
        db.query(SourceRecord)
        .filter(
            SourceRecord.person_id == person_id,
            SourceRecord.meeting_id.is_(None),
        )
        .order_by(desc(SourceRecord.captured_at))
        .limit(5)
        .all()
    )
    recent_sources = [
        SourceSummary(
            id=s.id,
            captured_at=s.captured_at.isoformat(),
            capture_type=s.capture_type,
            source_type="direct",
        )
        for s in direct_sources
    ]

    # Get timeline counts
    direct_count = (
        db.query(func.count(SourceRecord.id))
        .filter(
            SourceRecord.person_id == person_id,
            SourceRecord.meeting_id.is_(None),
        )
        .scalar()
    ) or 0

    meeting_count = (
        db.query(func.count(Meeting.id))
        .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
        .filter(MeetingParticipant.person_id == person_id)
        .scalar()
    ) or 0

    return PersonProfileResponse(
        id=person.id,
        name=person.name,
        type=person.type,
        role=person.role,
        tags=tag_list,
        last_interaction_at=person.last_interaction_at.isoformat() if person.last_interaction_at else None,
        recent_sources=recent_sources,
        timeline_summary=TimelineSummary(
            total_entries=direct_count + meeting_count,
            direct_count=direct_count,
            meeting_count=meeting_count,
        ),
    )


# ============================================================================
# Update Person (Epic 32.2 - role field)
# ============================================================================

@router.patch("/{person_id}", response_model=PersonResponse)
def update_person(
    person_id: str,
    request: PersonUpdateRequest,
    db: Session = Depends(get_db),
) -> PersonResponse:
    """Update person type and/or role."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    old_type = person.type
    old_role = person.role

    if request.type is not None:
        person_type = request.type.strip().lower()
        if person_type not in {"person", "org"}:
            raise HTTPException(status_code=422, detail="type must be person or org")
        person.type = person_type

    if request.role is not None:
        person.role = request.role.strip() if request.role.strip() else None

    person.updated_at = utcnow()

    add_audit_entry(
        db,
        action="person_updated",
        entity_type="Person",
        entity_id=person_id,
        payload={
            "old_type": old_type,
            "new_type": person.type,
            "old_role": old_role,
            "new_role": person.role,
        },
    )

    db.commit()

    return PersonResponse(
        id=person.id,
        name=person.name,
        type=person.type,
        role=person.role,
        last_interaction_at=person.last_interaction_at.isoformat() if person.last_interaction_at else None,
    )


# ============================================================================
# Person Tags (Epic 32.3)
# ============================================================================

@router.post(
    "/{person_id}/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_person_tag(
    person_id: str,
    request: TagRequest,
    db: Session = Depends(get_db),
) -> TagResponse:
    """Add a tag to a person."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    tag_value = request.tag.strip().lower()
    if not tag_value:
        raise HTTPException(status_code=422, detail="tag must not be blank")

    # Check if tag already exists
    existing = (
        db.query(PersonTag)
        .filter(PersonTag.person_id == person_id, func.lower(PersonTag.tag) == tag_value)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")

    tag_id = f"pt_{uuid4().hex}"
    tag = PersonTag(
        id=tag_id,
        person_id=person_id,
        tag=tag_value,
        created_at=utcnow(),
    )
    db.add(tag)

    add_audit_entry(
        db,
        action="person_tag_added",
        entity_type="PersonTag",
        entity_id=tag_id,
        payload={"person_id": person_id, "tag": tag_value},
    )

    db.commit()

    return TagResponse(id=tag_id, person_id=person_id, tag=tag_value)


@router.delete(
    "/{person_id}/tags/{tag}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_person_tag(
    person_id: str,
    tag: str,
    db: Session = Depends(get_db),
):
    """Remove a tag from a person."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    existing = (
        db.query(PersonTag)
        .filter(PersonTag.person_id == person_id, func.lower(PersonTag.tag) == tag.lower())
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag_id = existing.id
    db.delete(existing)

    add_audit_entry(
        db,
        action="person_tag_removed",
        entity_type="PersonTag",
        entity_id=tag_id,
        payload={"person_id": person_id, "tag": tag},
    )

    db.commit()
    return None


# ============================================================================
# Person Notes (Epic 32.1 - direct capture)
# ============================================================================

# Allowed capture types for person notes
ALLOWED_CAPTURE_TYPES = {
    "notes",
    "transcript",
    "observation",  # Care mode
    "symptom",      # Care mode
    "mood",         # Care mode
    "medication",   # Care mode
    "intake",       # Professional mode
}


@router.post(
    "/{person_id}/notes",
    response_model=PersonNoteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_person_note(
    person_id: str,
    request: PersonNoteRequest,
    db: Session = Depends(get_db),
) -> PersonNoteResponse:
    """
    Create a note directly attached to a person (no meeting required).

    Supports capture types:
    - Standard: notes, transcript
    - Care mode: observation, symptom, mood, medication
    - Professional mode: intake
    """
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    if request.capture_type not in ALLOWED_CAPTURE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capture_type. Allowed: {', '.join(sorted(ALLOWED_CAPTURE_TYPES))}",
        )

    job_id = f"j_{uuid4().hex}"
    job = IngestionJob(
        id=job_id,
        meeting_id=None,
        person_id=person_id,
        payload=request.payload,
        capture_type=request.capture_type,
        status="queued",
        created_at=utcnow(),
    )
    db.add(job)

    add_audit_entry(
        db,
        action="person_ingestion_queued",
        entity_type="IngestionJob",
        entity_id=job_id,
        payload={"person_id": person_id, "capture_type": request.capture_type},
    )

    db.commit()

    return PersonNoteResponse(job_id=job_id)


# ============================================================================
# Person Timeline (enhanced with direct sources)
# ============================================================================

@router.get("/{person_id}/timeline")
def person_timeline(
    person_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Get person timeline including both meeting-based and direct sources.

    Returns unified timeline sorted by occurred_at descending.
    """
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Get all meetings for this person
    meetings = (
        db.query(Meeting)
        .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
        .filter(MeetingParticipant.person_id == person_id)
        .order_by(desc(Meeting.starts_at), Meeting.id.asc())
        .all()
    )

    # Get person-direct sources (meeting_id is null)
    direct_sources = (
        db.query(SourceRecord)
        .filter(
            SourceRecord.person_id == person_id,
            SourceRecord.meeting_id.is_(None),
        )
        .order_by(desc(SourceRecord.captured_at))
        .all()
    )

    # Build unified timeline
    timeline = []

    # Add meeting-based entries
    for meeting in meetings:
        source = (
            db.query(SourceRecord)
            .filter(SourceRecord.meeting_id == meeting.id)
            .order_by(SourceRecord.captured_at.desc())
            .first()
        )
        timeline.append({
            "occurred_at": source.captured_at if source else meeting.starts_at,
            "source_type": "meeting",
            "meeting_id": meeting.id,
            "meeting_title": meeting.title,
            "meeting_starts_at": meeting.starts_at,
            "source_id": source.id if source else None,
            "capture_type": source.capture_type if source else None,
            "source_missing": source is None,
        })

    # Add direct source entries
    for source in direct_sources:
        timeline.append({
            "occurred_at": source.captured_at,
            "source_type": "direct",
            "source_id": source.id,
            "capture_type": source.capture_type,
            "source_missing": False,
        })

    # Sort by occurred_at descending
    timeline.sort(key=lambda x: x["occurred_at"], reverse=True)

    return {
        "person": {
            "id": person.id,
            "name": person.name,
            "type": person.type,
            "role": person.role,
            "last_interaction_at": person.last_interaction_at,
        },
        "timeline": timeline,
    }


# ============================================================================
# Person Continuity
# ============================================================================

@router.get("/{person_id}/continuity")
def person_continuity(
    person_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Get person continuity view with source-linked summaries.

    Returns ordered continuity entries for meetings and direct sources.
    """
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Get meeting-based sources
    meetings = (
        db.query(Meeting)
        .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
        .filter(MeetingParticipant.person_id == person_id)
        .order_by(desc(Meeting.starts_at), Meeting.id.asc())
        .all()
    )

    meeting_ids = [meeting.id for meeting in meetings]
    latest_sources: dict[str, SourceRecord] = {}

    if meeting_ids:
        latest = (
            db.query(
                SourceRecord.meeting_id.label("meeting_id"),
                func.max(SourceRecord.captured_at).label("max_captured"),
            )
            .filter(SourceRecord.meeting_id.in_(meeting_ids))
            .group_by(SourceRecord.meeting_id)
            .subquery()
        )
        sources = (
            db.query(SourceRecord)
            .join(
                latest,
                (SourceRecord.meeting_id == latest.c.meeting_id)
                & (SourceRecord.captured_at == latest.c.max_captured),
            )
            .all()
        )
        latest_sources = {source.meeting_id: source for source in sources}

    # Get direct sources for this person
    direct_sources = (
        db.query(SourceRecord)
        .filter(
            SourceRecord.person_id == person_id,
            SourceRecord.meeting_id.is_(None),
        )
        .order_by(desc(SourceRecord.captured_at))
        .all()
    )

    continuity: list[dict] = []

    # Add meeting-based continuity
    for meeting in meetings:
        source = latest_sources.get(meeting.id)
        summary = (
            f"Context captured via {source.capture_type}."
            if source
            else "No recent context available."
        )
        continuity.append({
            "occurred_at": meeting.starts_at,
            "source_type": "meeting",
            "meeting_id": meeting.id,
            "meeting_title": meeting.title,
            "source_id": source.id if source else None,
            "source_missing": source is None,
            "summary": summary,
        })

    # Add direct sources to continuity
    for source in direct_sources:
        continuity.append({
            "occurred_at": source.captured_at,
            "source_type": "direct",
            "source_id": source.id,
            "source_missing": False,
            "summary": f"Direct note captured via {source.capture_type}.",
        })

    # Sort by occurred_at descending
    continuity.sort(key=lambda x: x["occurred_at"], reverse=True)

    return {
        "person": {
            "id": person.id,
            "name": person.name,
            "type": person.type,
            "role": person.role,
            "last_interaction_at": person.last_interaction_at,
        },
        "continuity": continuity,
    }


# ============================================================================
# Remove Person from Meeting Timeline
# ============================================================================

@router.delete("/{person_id}/timeline/{meeting_id}")
def remove_person_timeline_link(
    person_id: str,
    meeting_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Remove a person from a meeting's participant list."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    link = (
        db.query(MeetingParticipant)
        .filter(
            MeetingParticipant.person_id == person_id,
            MeetingParticipant.meeting_id == meeting_id,
        )
        .first()
    )

    if not link:
        return {"removed": False}

    db.delete(link)

    add_audit_entry(
        db,
        action="person_timeline_link_removed",
        entity_type="MeetingParticipant",
        entity_id=f"{person_id}_{meeting_id}",
        payload={"person_id": person_id, "meeting_id": meeting_id},
    )

    db.commit()

    return {"removed": True}
