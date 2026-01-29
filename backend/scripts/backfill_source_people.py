import json

from app.db import SessionLocal, init_db
from app.models.ingestion_job import IngestionJob
from app.models.source_record import SourceRecord


def normalize_people(value: str | None) -> str:
    if not value:
        return "[]"
    try:
        raw = json.loads(value)
        ids = [pid for pid in raw if isinstance(pid, str) and pid]
        return json.dumps(ids)
    except Exception:
        return "[]"


def main() -> None:
    init_db()
    session = SessionLocal()
    try:
        sources = (
            session.query(SourceRecord)
            .filter(SourceRecord.people_ids.is_(None))
            .all()
        )
        if not sources:
            print({"sources_updated": 0})
            return
        by_source_id = {source.id: source for source in sources}
        jobs = (
            session.query(IngestionJob.source_id, IngestionJob.people_ids)
            .filter(IngestionJob.source_id.in_(by_source_id.keys()))
            .all()
        )
        updated = 0
        for source_id, people_ids in jobs:
            source = by_source_id.get(source_id)
            if not source:
                continue
            source.people_ids = normalize_people(people_ids)
            updated += 1
        # For any sources without jobs, set to explicit empty list
        for source in sources:
            if source.people_ids is None:
                source.people_ids = "[]"
                updated += 1
        session.commit()
        print({"sources_updated": updated})
    finally:
        session.close()


if __name__ == "__main__":
    main()
