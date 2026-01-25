from __future__ import annotations

from datetime import datetime

from app.db import SessionLocal, init_db
from app.models.ingestion_job import IngestionJob
from app.models.meeting import Meeting
from app.ops.qdrant_store import add_documents


def _make_excerpt(payload: str | None, limit: int = 200) -> str:
    if not payload:
        return "No capture excerpt available."
    excerpt = payload.strip()
    if len(excerpt) > limit:
        excerpt = f"{excerpt[: limit - 1]}…"
    return excerpt


def main() -> None:
    init_db()
    session = SessionLocal()
    indexed = 0
    skipped = 0
    try:
        jobs = (
            session.query(IngestionJob)
            .filter(IngestionJob.status == "succeeded")
            .filter(IngestionJob.source_id != None)  # noqa: E711
            .filter(IngestionJob.payload != None)  # noqa: E711
            .order_by(
                IngestionJob.completed_at.asc().nulls_last(),
                IngestionJob.created_at.asc(),
            )
            .all()
        )
        for job in jobs:
            if not job.payload or not job.source_id:
                skipped += 1
                continue
            meeting = session.query(Meeting).filter(Meeting.id == job.meeting_id).first()
            meeting_title = meeting.title if meeting else "Context"
            captured_at = job.completed_at or job.created_at or datetime.utcnow()
            add_documents(
                documents=[job.payload],
                metadata=[
                    {
                        "source_id": job.source_id,
                        "meeting_id": job.meeting_id,
                        "meeting_title": meeting_title,
                        "captured_at": captured_at.isoformat(),
                        "capture_type": job.capture_type,
                        "excerpt": _make_excerpt(job.payload),
                    }
                ],
                ids=[job.source_id],
            )
            indexed += 1
    finally:
        session.close()
    print({"indexed": indexed, "skipped": skipped})


if __name__ == "__main__":
    main()
