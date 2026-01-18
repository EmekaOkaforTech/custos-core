import random
import sys
from datetime import datetime, timedelta
from uuid import uuid4

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_db
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.source_record import SourceRecord


def seed_meetings(count: int, sources_per_meeting: int) -> None:
    init_db()
    session = SessionLocal()
    try:
        people = []
        for i in range(50):
            person_id = f"p_seed_{i}"
            person = Person(id=person_id, name=f"Person {i}", type="person")
            session.add(person)
            people.append(person_id)
        session.commit()

        now = datetime.utcnow()
        for i in range(count):
            meeting_id = f"m_seed_{uuid4().hex}"
            start = now - timedelta(days=random.randint(0, 120), hours=random.randint(0, 23))
            meeting = Meeting(
                id=meeting_id,
                title=f"Meeting {i}",
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                source="seed",
            )
            session.add(meeting)
            for _ in range(random.randint(1, 3)):
                person_id = random.choice(people)
                session.add(MeetingParticipant(meeting_id=meeting_id, person_id=person_id))

            for j in range(sources_per_meeting):
                source_id = f"s_seed_{uuid4().hex}"
                captured_at = start + timedelta(minutes=j)
                source = SourceRecord(
                    id=source_id,
                    meeting_id=meeting_id,
                    captured_at=captured_at,
                    capture_type="notes",
                    uri=f"local://sources/{source_id}",
                )
                session.add(source)

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed_meetings(1000, 2)
    print("Seeded meetings and sources.")
