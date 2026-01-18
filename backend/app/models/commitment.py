from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from .base import Base


class Commitment(Base):
    __tablename__ = "commitment"

    id = Column(String, primary_key=True)
    text = Column(String, nullable=False)
    due_at = Column(DateTime, nullable=True)
    acknowledged = Column(Boolean, default=False, nullable=False)
    source_id = Column(String, ForeignKey("source_record.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
