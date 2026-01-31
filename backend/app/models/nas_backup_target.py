"""NAS backup target configuration.

Epic 41: Home Network Architecture - Story 41.2
Stores configuration for encrypted backups to SMB/NFS mounted paths.
"""

from datetime import datetime, UTC

from sqlalchemy import Boolean, Column, DateTime, String, Text

from .base import Base


def _utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


class NasBackupTarget(Base):
    __tablename__ = "nas_backup_target"

    id = Column(String, primary_key=True)
    protocol = Column(String, nullable=False)  # smb | nfs
    host = Column(String, nullable=True)
    share = Column(String, nullable=True)
    mount_path = Column(String, nullable=False)  # local mount path
    username = Column(String, nullable=True)
    password = Column(Text, nullable=True)
    enabled = Column(Boolean, default=False, nullable=False)
    last_backup_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)
