from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, String, Text

from .base import Base
from app.utils.datetime import utcnow


class SourceRecord(Base):
    """Source record for captured context (meeting-based or person-direct)."""

    __tablename__ = "source_record"
    __table_args__ = (
        CheckConstraint(
            "(meeting_id IS NOT NULL) OR (person_id IS NOT NULL)",
            name="ck_source_record_has_context",
        ),
    )

    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meeting.id"), nullable=True, index=True)
    person_id = Column(String, ForeignKey("person.id"), nullable=True, index=True)  # Epic 32: direct person notes
    captured_at = Column(DateTime, nullable=False)
    capture_type = Column(String, nullable=False)
    uri = Column(String, nullable=False)
    relevant_at = Column(DateTime, nullable=True)
    dedupe_key = Column(String, nullable=True, index=True, unique=True)
    index_in_memory = Column(Boolean, nullable=False, default=False)
    people_ids = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
