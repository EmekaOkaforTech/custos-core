from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, Boolean

from .base import Base


class CalendarConnection(Base):
    __tablename__ = "calendar_connection"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False)
    scopes = Column(Text, nullable=False)
    token = Column(Text, nullable=False)
    enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
