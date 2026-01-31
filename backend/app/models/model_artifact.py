from datetime import datetime
from sqlalchemy import Column, DateTime, String

from app.models.base import Base


class ModelArtifact(Base):
    __tablename__ = "model_artifact"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    path = Column(String, nullable=False)
    format = Column(String, nullable=True)
    accelerator = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
