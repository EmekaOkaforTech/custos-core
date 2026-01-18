from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.calendar.provider import CalendarProvider
from app.calendar.status import mark_attempt, mark_success
from app.calendar.utils import normalize_identifier
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.settings import get_calendar_enabled


def ingest_calendar(provider: CalendarProvider, db: Session) -> dict:
    enabled = get_calendar_enabled()
    if not enabled:
        mark_attempt(enabled=False)
        return {"status": "disabled"}

    try:
        now = datetime.utcnow()
        events = provider.list_events(now - timedelta(days=1), now + timedelta(days=7))
        for event in events:
            meeting_id = f"m_cal_{event.event_id}"
            meeting = db.get(Meeting, meeting_id)
            if not meeting:
                meeting = Meeting(
                    id=meeting_id,
                    title=event.title,
                    starts_at=event.starts_at,
                    ends_at=event.ends_at,
                    source="calendar",
                )
                db.add(meeting)
            else:
                meeting.title = event.title
                meeting.starts_at = event.starts_at
                meeting.ends_at = event.ends_at
                meeting.source = "calendar"

            attendees = provider.list_attendees(event.event_id)
            for attendee in attendees:
                person_id = f"p_cal_{normalize_identifier(attendee.identifier)}"
                person = db.get(Person, person_id)
                if not person:
                    person = Person(
                        id=person_id,
                        name=attendee.display_name or attendee.identifier,
                        type="person",
                        last_interaction_at=event.starts_at,
                    )
                    db.add(person)
                else:
                    if not person.last_interaction_at or event.starts_at > person.last_interaction_at:
                        person.last_interaction_at = event.starts_at

                link = (
                    db.query(MeetingParticipant)
                    .filter_by(meeting_id=meeting_id, person_id=person_id)
                    .first()
                )
                if not link:
                    db.add(MeetingParticipant(meeting_id=meeting_id, person_id=person_id))

        db.commit()
        mark_success(enabled=True)
        return {"status": "ok", "events": len(events)}
    except Exception:
        db.rollback()
        mark_attempt(enabled=True, error="calendar_ingest_failed")
        return {"status": "failed"}
