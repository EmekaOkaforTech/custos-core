from sqlalchemy import Column, DateTime, String

from .base import Base
from app.utils.datetime import utcnow


class Person(Base):
    """Person entity for contacts, clients, care recipients, etc."""

    __tablename__ = "person"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True, index=True)  # Story 37.3: Calendar attendee matching
    type = Column(String, nullable=False)
    role = Column(String, nullable=True)  # Epic 32: e.g., "client", "family", "colleague"
    last_interaction_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
