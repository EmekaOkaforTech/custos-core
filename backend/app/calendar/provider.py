from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    title: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class CalendarAttendee:
    identifier: str
    display_name: str | None


class CalendarProvider(Protocol):
    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        ...

    def get_event(self, event_id: str) -> CalendarEvent | None:
        ...

    def list_attendees(self, event_id: str) -> list[CalendarAttendee]:
        ...
