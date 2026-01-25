from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from .base import Base


class SourceRecord(Base):
    __tablename__ = "source_record"

    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meeting.id"), nullable=False, index=True)
    captured_at = Column(DateTime, nullable=False)
    capture_type = Column(String, nullable=False)
    uri = Column(String, nullable=False)
    relevant_at = Column(DateTime, nullable=True)
    dedupe_key = Column(String, nullable=True, index=True, unique=True)
    index_in_memory = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
