from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
