from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from .base import Base


class IngestionJob(Base):
    __tablename__ = "ingestion_job"

    id = Column(String, primary_key=True)
    meeting_id = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    capture_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
