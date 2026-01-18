from sqlalchemy import Column, ForeignKey, String

from .base import Base


class MeetingParticipant(Base):
    __tablename__ = "meeting_participant"

    meeting_id = Column(String, ForeignKey("meeting.id"), primary_key=True, index=True)
    person_id = Column(String, ForeignKey("person.id"), primary_key=True, index=True)
