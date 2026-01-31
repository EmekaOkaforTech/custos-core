from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, String, Text

from .base import Base
from app.utils.datetime import utcnow


class IngestionJob(Base):
    """Ingestion job for processing captured context."""

    __tablename__ = "ingestion_job"
    __table_args__ = (
        CheckConstraint(
            "(meeting_id IS NOT NULL) OR (person_id IS NOT NULL)",
            name="ck_ingestion_job_has_context",
        ),
    )

    id = Column(String, primary_key=True)
    meeting_id = Column(String, nullable=True)  # Nullable for person-direct notes
    person_id = Column(String, nullable=True)  # Epic 32: direct person notes
    payload = Column(Text, nullable=False)
    media_path = Column(Text, nullable=True)
    capture_type = Column(String, nullable=False)
    people_ids = Column(Text, nullable=True)
    source_id = Column(String, nullable=True)
    relevant_at = Column(DateTime, nullable=True)
    commitment_relevant_by = Column(DateTime, nullable=True)
    index_in_memory = Column(Boolean, nullable=False, default=False)
    dedupe_key = Column(String, nullable=True, index=True, unique=True)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
