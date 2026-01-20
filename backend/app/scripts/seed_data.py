from __future__ import annotations

from datetime import datetime, timedelta

from app.db import SessionLocal, init_db
from app.models.commitment import Commitment
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.person import Person
from app.models.source_record import SourceRecord


def seed() -> dict[str, int]:
    init_db()
    session = SessionLocal()
    created = {"people": 0, "meetings": 0, "participants": 0, "sources": 0, "commitments": 0}
    try:
        org = session.get(Person, "p_seed_org")
        if not org:
            org = Person(id="p_seed_org", name="Seed Org", type="org")
            session.add(org)
            created["people"] += 1

        individual = session.get(Person, "p_seed_person")
        if not individual:
            individual = Person(id="p_seed_person", name="Seed Person", type="person")
            session.add(individual)
            created["people"] += 1

        meeting = session.get(Meeting, "m_seed_001")
        if not meeting:
            now = datetime.utcnow()
            meeting = Meeting(
                id="m_seed_001",
                title="Seed Planning Sync",
                starts_at=now + timedelta(days=1),
                ends_at=now + timedelta(days=1, hours=1),
                source="seed",
            )
            session.add(meeting)
            created["meetings"] += 1

        if not session.get(MeetingParticipant, {"meeting_id": "m_seed_001", "person_id": "p_seed_org"}):
            session.add(MeetingParticipant(meeting_id="m_seed_001", person_id="p_seed_org"))
            created["participants"] += 1
        if not session.get(MeetingParticipant, {"meeting_id": "m_seed_001", "person_id": "p_seed_person"}):
            session.add(MeetingParticipant(meeting_id="m_seed_001", person_id="p_seed_person"))
            created["participants"] += 1

        source = session.get(SourceRecord, "sr_seed_001")
        if not source:
            source = SourceRecord(
                id="sr_seed_001",
                meeting_id="m_seed_001",
                captured_at=datetime.utcnow(),
                capture_type="notes",
                uri="seed://meeting/m_seed_001",
            )
            session.add(source)
            created["sources"] += 1

        commitment = session.get(Commitment, "c_seed_001")
        if not commitment:
            commitment = Commitment(
                id="c_seed_001",
                text="Send seed follow-up summary.",
                due_at=datetime.utcnow() + timedelta(days=2),
                acknowledged=False,
                source_id="sr_seed_001",
            )
            session.add(commitment)
            created["commitments"] += 1

        session.commit()
        return created
    finally:
        session.close()


def main() -> None:
    created = seed()
    print(created)


if __name__ == "__main__":
    main()
