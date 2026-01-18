from datetime import datetime, timedelta

from app.calendar.provider import CalendarAttendee, CalendarEvent


class DemoCalendarProvider:
    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        demo_start = start + timedelta(hours=2)
        demo_end = demo_start + timedelta(hours=1)
        return [
            CalendarEvent(
                event_id="demo-1",
                title="Northwind Status Call",
                starts_at=demo_start,
                ends_at=demo_end,
            )
        ]

    def get_event(self, event_id: str) -> CalendarEvent | None:
        if event_id != "demo-1":
            return None
        now = datetime.utcnow()
        return CalendarEvent(
            event_id="demo-1",
            title="Northwind Status Call",
            starts_at=now + timedelta(hours=2),
            ends_at=now + timedelta(hours=3),
        )

    def list_attendees(self, event_id: str) -> list[CalendarAttendee]:
        if event_id != "demo-1":
            return []
        return [
            CalendarAttendee(identifier="alex@example.com", display_name="Alex Morgan"),
            CalendarAttendee(identifier="sarah@example.com", display_name="Sarah Patel"),
        ]
