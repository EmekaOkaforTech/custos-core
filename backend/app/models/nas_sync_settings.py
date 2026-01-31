"""NAS sync settings for home device sync.

Epic 41: Home Network Architecture - Story 41.4
"""

from datetime import datetime, UTC

from sqlalchemy import Boolean, Column, DateTime, String, Text

from .base import Base


def _utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


class NasSyncSettings(Base):
    __tablename__ = "nas_sync_settings"

    id = Column(String, primary_key=True)
    mount_path = Column(String, nullable=False)
    enabled = Column(Boolean, default=False, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)
