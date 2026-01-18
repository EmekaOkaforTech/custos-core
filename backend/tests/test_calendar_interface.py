import inspect

from app.calendar.provider import CalendarProvider


def test_calendar_provider_is_read_only():
    methods = {name for name, _ in inspect.getmembers(CalendarProvider, predicate=inspect.isfunction)}
    forbidden = {"create_event", "update_event", "delete_event", "write_event"}
    assert not (methods & forbidden)
