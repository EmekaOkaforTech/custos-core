import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_db
from app.main import app
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.source_record import SourceRecord


def seed_data():
    init_db()
    session = SessionLocal()
    try:
        person = Person(id="p_perf", name="Perf User", type="person")
        session.add(person)
        now = datetime.utcnow()
        for i in range(1000):
            meeting_id = f"m_perf_{uuid4().hex}"
            start = now - timedelta(days=i % 120, hours=i % 24)
            meeting = Meeting(
                id=meeting_id,
                title=f"Perf Meeting {i}",
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                source="seed",
            )
            session.add(meeting)
            session.add(MeetingParticipant(meeting_id=meeting_id, person_id="p_perf"))
            for j in range(2):
                source_id = f"s_perf_{uuid4().hex}"
                source = SourceRecord(
                    id=source_id,
                    meeting_id=meeting_id,
                    captured_at=start + timedelta(minutes=j),
                    capture_type="notes",
                    uri=f"local://sources/{source_id}",
                )
                session.add(source)
        session.commit()
    finally:
        session.close()


def measure_endpoint(client, path, iterations=25):
    timings = []
    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get(path)
        _ = response.json()
        timings.append(time.perf_counter() - start)
    timings.sort()
    p95 = timings[int(0.95 * len(timings)) - 1]
    return p95


def run():
    seed_data()
    client = TestClient(app)
    p95_next = measure_endpoint(client, "/api/briefings/next")
    p95_today = measure_endpoint(client, "/api/briefings/today")
    p95_timeline = measure_endpoint(client, "/api/people/p_perf/timeline")
    print({
        "p95_briefings_next_sec": p95_next,
        "p95_briefings_today_sec": p95_today,
        "p95_people_timeline_sec": p95_timeline,
    })


if __name__ == "__main__":
    run()
