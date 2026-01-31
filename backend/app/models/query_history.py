from sqlalchemy import Column, DateTime, String, Text

from .base import Base
from app.utils.datetime import utcnow


class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(String, primary_key=True)
    query_text = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    filters = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
