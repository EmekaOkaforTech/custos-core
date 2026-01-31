from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base
from app.utils.datetime import utcnow


class EmailMessage(Base):
    __tablename__ = 'email_message'

    id = Column(Integer, primary_key=True)
    message_id = Column(String, nullable=False, index=True, unique=True)
    thread_id = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    to_emails = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    meeting_id = Column(String, ForeignKey('meeting.id'), nullable=True, index=True)
    source_id = Column(String, ForeignKey('source_record.id'), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
