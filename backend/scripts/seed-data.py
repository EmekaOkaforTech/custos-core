import os
from datetime import datetime, timedelta
from uuid import uuid4

from app.db import SessionLocal, init_db
from app.models.commitment import Commitment
from app.models.meeting import Meeting
from app.models.source_record import SourceRecord


def main():
    if not os.getenv("CUSTOS_DATABASE_KEY"):
        raise RuntimeError("CUSTOS_DATABASE_KEY is required")

    init_db()
    session = SessionLocal()
    try:
        meeting_id = f"m_{uuid4().hex}"
        source_id = f"s_{uuid4().hex}"
        commitment_id = f"c_{uuid4().hex}"
        now = datetime.utcnow()

        meeting = Meeting(
            id=meeting_id,
            title="Northwind Status Call",
            starts_at=now + timedelta(hours=2),
            ends_at=now + timedelta(hours=3),
        )
        source = SourceRecord(
            id=source_id,
            meeting_id=meeting_id,
            captured_at=now - timedelta(days=6),
            capture_type="notes",
            uri=f"local://sources/{source_id}",
        )
        commitment = Commitment(
            id=commitment_id,
            text="Send pricing follow-up",
            due_at=None,
            acknowledged=False,
            source_id=source_id,
        )

        session.add(meeting)
        session.add(source)
        session.add(commitment)
        session.commit()
        print("Seeded meeting, source, and commitment.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
