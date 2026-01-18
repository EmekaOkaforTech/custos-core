import time

from app.calendar.demo_provider import DemoCalendarProvider
from app.calendar.ingest import ingest_calendar
from app.db import SessionLocal
from app.settings import get_calendar_enabled, get_calendar_poll_seconds


def run_once():
    if not get_calendar_enabled():
        return
    session = SessionLocal()
    try:
        ingest_calendar(DemoCalendarProvider(), session)
    finally:
        session.close()


def run_forever():
    while True:
        run_once()
        time.sleep(get_calendar_poll_seconds())


if __name__ == "__main__":
    run_forever()
