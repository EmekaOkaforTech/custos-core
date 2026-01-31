from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db import Base


class InferenceTask(Base):
    __tablename__ = inference_task

    id = Column(String, primary_key=True)
    task_type = Column(String, nullable=False)
    payload = Column(Text, nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    status = Column(String, default=queued, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
