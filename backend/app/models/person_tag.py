from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint

from .base import Base
from app.utils.datetime import utcnow


class PersonTag(Base):
    """Lightweight user-defined tags for people (Epic 32)."""

    __tablename__ = "person_tag"
    __table_args__ = (
        UniqueConstraint("person_id", "tag", name="uq_person_tag"),
    )

    id = Column(String, primary_key=True)
    person_id = Column(String, ForeignKey("person.id"), nullable=False, index=True)
    tag = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
