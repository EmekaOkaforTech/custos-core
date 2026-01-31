from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class SummarizationSettings(Base):
    __tablename__ = 'summarization_settings'

    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, nullable=False, server_default='0')
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    max_input_tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
