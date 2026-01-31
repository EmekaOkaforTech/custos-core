from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.db import Base


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False)
    channel_id = Column(String, nullable=True)
    channel_name = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    user_name = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    meeting_id = Column(String, nullable=True)
    person_id = Column(String, nullable=True)
    source_id = Column(String, nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
