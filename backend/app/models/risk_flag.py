from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String

from .base import Base


class RiskFlag(Base):
    __tablename__ = "risk_flag"

    id = Column(String, primary_key=True)
    source_id = Column(String, ForeignKey("source_record.id"), nullable=False, index=True)
    flag_type = Column(String, nullable=False)
    rule_id = Column(String, nullable=False)
    excerpt = Column(String, nullable=False)
    captured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
