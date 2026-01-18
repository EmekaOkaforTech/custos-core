from datetime import datetime

from sqlalchemy import Column, DateTime, String

from .base import Base


class Meeting(Base):
    __tablename__ = "meeting"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False, index=True)
    ends_at = Column(DateTime, nullable=False)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
