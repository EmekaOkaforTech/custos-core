from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.models.base import Base
from app.utils.datetime import utcnow


class EmailConnection(Base):
    __tablename__ = 'email_connection'

    id = Column(Integer, primary_key=True)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False, default=993)
    username = Column(String, nullable=False)
    password = Column(String, nullable=True)
    use_tls = Column(Boolean, nullable=False, default=True)
    enabled = Column(Boolean, nullable=False, default=False)
    poll_interval_minutes = Column(Integer, nullable=False, default=30)
    last_uid = Column(Integer, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    last_attempt = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, nullable=False)
