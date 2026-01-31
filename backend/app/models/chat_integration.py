from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String

from app.db import Base


class ChatIntegration(Base):
    __tablename__ = "chat_integration"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False)
    secret = Column(String, nullable=True)
    enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
