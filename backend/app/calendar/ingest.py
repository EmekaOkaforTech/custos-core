"""Calendar event ingestion and sync logic.

Epic 37: Live Calendar Sync - Stories 37.2, 37.3
Creates/updates Meeting records from calendar events, handles deletions gracefully.
Story 37.3: Uses PersonMatcher for intelligent attendee matching.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.calendar.person_matcher import PersonMatcher
from app.calendar.provider import CalendarProvider
from app.calendar.status import mark_attempt, mark_success
from app.models.calendar_connection import CalendarConnection
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.settings import get_calendar_enabled

logger = logging.getLogger(__name__)


def _utc_now():
    """Return current UTC time without timezone info for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


def ingest_calendar(
    provider: CalendarProvider,
    db: Session,
    connection_id: str | None = None,
) -> dict:
    """Ingest calendar events and sync with local Meeting records.

    Creates or updates Meeting records from calendar events.
    Marks meetings as cancelled if they no longer exist in the calendar.
    Updates CalendarConnection sync tracking fields.

    Args:
        provider: Calendar provider implementation
        db: Database session
        connection_id: Optional ID of the CalendarConnection (Story 37.5)

    Returns:
        dict with sync status, event count, and any errors
    """
    enabled = get_calendar_enabled()
    if not enabled:
        mark_attempt(enabled=False)
        return {"status": "disabled"}

    try:
        now = _utc_now()
        start_range = now - timedelta(days=1)
        end_range = now + timedelta(days=7)

        # Fetch events from provider
        events = provider.list_events(start_range, end_range)
        synced_event_ids = set()

        for event in events:
            meeting_id = f"m_cal_{event.event_id}"
            synced_event_ids.add(meeting_id)

            meeting = db.get(Meeting, meeting_id)
            if not meeting:
                meeting = Meeting(
                    id=meeting_id,
                    title=event.title,
                    starts_at=event.starts_at,
                    ends_at=event.ends_at,
                    source="calendar",
                    calendar_source_id=connection_id,  # Story 37.5: Track source calendar
                )
                db.add(meeting)
                logger.debug("Created meeting: %s", meeting_id)
            else:
                # Story 37.4: Handle local overrides
                if meeting.local_override:
                    # Store latest calendar values for conflict detection, but don't update meeting
                    meeting.calendar_title = event.title
                    meeting.calendar_starts_at = event.starts_at
                    meeting.calendar_ends_at = event.ends_at
                    logger.debug("Meeting has local override, storing calendar values: %s", meeting_id)
                else:
                    # No local override - update normally
                    meeting.title = event.title
                    meeting.starts_at = event.starts_at
                    meeting.ends_at = event.ends_at
                    meeting.source = "calendar"

                # Restore if previously cancelled
                if meeting.cancelled_at is not None:
                    meeting.cancelled_at = None
                    logger.debug("Restored cancelled meeting: %s", meeting_id)

            # Process attendees using PersonMatcher (Story 37.3)
            person_matcher = PersonMatcher(db)
            attendees = provider.list_attendees(event.event_id)
            for attendee in attendees:
                # Use PersonMatcher for intelligent matching
                match_result = person_matcher.find_or_create_person(
                    email=attendee.identifier,
                    name=attendee.display_name,
                    source="calendar",
                    event_id=event.event_id,
                )
                person_id = match_result.person_id

                # Update last_interaction_at for matched/created person
                person = db.get(Person, person_id)
                if person:
                    if not person.last_interaction_at or event.starts_at > person.last_interaction_at:
                        person.last_interaction_at = event.starts_at

                # Link person to meeting
                link = (
                    db.query(MeetingParticipant)
                    .filter_by(meeting_id=meeting_id, person_id=person_id)
                    .first()
                )
                if not link:
                    db.add(MeetingParticipant(meeting_id=meeting_id, person_id=person_id))

        # Handle deletions: mark calendar meetings not in current sync as cancelled
        # Only process meetings within the sync time range
        existing_calendar_meetings = (
            db.query(Meeting)
            .filter(
                Meeting.source == "calendar",
                Meeting.id.like("m_cal_%"),
                Meeting.starts_at >= start_range,
                Meeting.starts_at <= end_range,
                Meeting.cancelled_at == None,  # noqa: E711
            )
            .all()
        )

        cancelled_count = 0
        for meeting in existing_calendar_meetings:
            if meeting.id not in synced_event_ids:
                meeting.cancelled_at = now
                cancelled_count += 1
                logger.debug("Marked meeting as cancelled: %s", meeting.id)

        # Update CalendarConnection sync tracking
        if connection_id:
            connection = db.get(CalendarConnection, connection_id)
        else:
            # Fallback to first enabled connection for backwards compatibility
            connection = (
                db.query(CalendarConnection)
                .filter(CalendarConnection.enabled.is_(True))
                .first()
            )
        if connection:
            connection.last_sync_at = now
            connection.sync_error = None  # Clear any previous error

        db.commit()
        mark_success(enabled=True)

        result = {
            "status": "ok",
            "events": len(events),
            "cancelled": cancelled_count,
        }
        logger.info("Calendar sync complete: %d events, %d cancelled", len(events), cancelled_count)
        return result

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error("Calendar ingest failed: %s", error_msg)

        # Update connection with sync error
        try:
            if connection_id:
                connection = db.get(CalendarConnection, connection_id)
            else:
                connection = (
                    db.query(CalendarConnection)
                    .filter(CalendarConnection.enabled.is_(True))
                    .first()
                )
            if connection:
                connection.sync_error = error_msg
                db.commit()
        except Exception:
            pass  # Don't fail if we can't update error status

        mark_attempt(enabled=True, error="calendar_ingest_failed")
        return {"status": "failed", "error": error_msg}
