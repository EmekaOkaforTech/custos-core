from collections import defaultdict
from datetime import datetime

from app.db import SessionLocal, init_db
from app.models.commitment import Commitment
from app.models.ingestion_job import IngestionJob
from app.models.source_record import SourceRecord
from app.models.meeting import Meeting


def _normalize_payload(payload: str | None) -> str:
    if not payload:
        return ""
    return " ".join(payload.strip().split()).lower()


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.strip().split()).lower()


def dedupe_ingestion() -> dict:
    init_db()
    session = SessionLocal()
    summary = {
        "groups": 0,
        "jobs_marked": 0,
        "sources_deleted": 0,
        "commitments_deleted": 0,
        "commitment_groups": 0,
        "commitments_deduped": 0,
    }
    try:
        jobs = (
            session.query(IngestionJob)
            .filter(IngestionJob.status == "succeeded")
            .filter(IngestionJob.source_id != None)  # noqa: E711
            .all()
        )
        groups: dict[tuple[str, str, str, str], list[IngestionJob]] = defaultdict(list)
        for job in jobs:
            key = (
                job.meeting_id,
                job.capture_type,
                _normalize_payload(job.payload),
                (job.people_ids or "").strip(),
                job.relevant_at.isoformat() if job.relevant_at else "",
            )
            groups[key].append(job)

        duplicate_source_ids: set[str] = set()
        for group in groups.values():
            if len(group) < 2:
                continue
            summary["groups"] += 1
            group.sort(
                key=lambda item: (
                    item.completed_at or datetime.min,
                    item.created_at or datetime.min,
                )
            )
            canonical = group[0]
            for dup in group[1:]:
                if dup.source_id and dup.source_id != canonical.source_id:
                    duplicate_source_ids.add(dup.source_id)
                dup.source_id = canonical.source_id
                dup.error = "deduped"
                summary["jobs_marked"] += 1

        if duplicate_source_ids:
            summary["commitments_deleted"] = (
                session.query(Commitment)
                .filter(Commitment.source_id.in_(duplicate_source_ids))
                .delete(synchronize_session=False)
            )
            summary["sources_deleted"] = (
                session.query(SourceRecord)
                .filter(SourceRecord.id.in_(duplicate_source_ids))
                .delete(synchronize_session=False)
            )

        session.commit()
        # Deduplicate commitments that share the same meeting + capture_type + text
        commitments = (
            session.query(Commitment, SourceRecord, Meeting)
            .join(SourceRecord, Commitment.source_id == SourceRecord.id)
            .join(Meeting, SourceRecord.meeting_id == Meeting.id)
            .all()
        )
        commitment_groups: dict[tuple[str, str, str], list[Commitment]] = defaultdict(list)
        for commitment, source, meeting in commitments:
            key = (meeting.id, source.capture_type, _normalize_text(commitment.text))
            commitment_groups[key].append(commitment)
        to_delete_ids: list[str] = []
        for group in commitment_groups.values():
            if len(group) < 2:
                continue
            summary["commitment_groups"] += 1
            group.sort(key=lambda item: (item.created_at or datetime.min, item.id))
            for dup in group[1:]:
                to_delete_ids.append(dup.id)
        if to_delete_ids:
            summary["commitments_deduped"] = (
                session.query(Commitment)
                .filter(Commitment.id.in_(to_delete_ids))
                .delete(synchronize_session=False)
            )
        # Remove orphaned sources without commitments
        orphan_sources = (
            session.query(SourceRecord.id)
            .outerjoin(Commitment, Commitment.source_id == SourceRecord.id)
            .filter(Commitment.id == None)  # noqa: E711
            .all()
        )
        orphan_ids = [sid for (sid,) in orphan_sources]
        if orphan_ids:
            summary["sources_deleted"] += (
                session.query(SourceRecord)
                .filter(SourceRecord.id.in_(orphan_ids))
                .delete(synchronize_session=False)
            )
        session.commit()
        return summary
    finally:
        session.close()


if __name__ == "__main__":
    result = dedupe_ingestion()
    print(result)
