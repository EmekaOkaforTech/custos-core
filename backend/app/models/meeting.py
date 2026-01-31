"""Meeting model for storing calendar events and meeting records.

Epic 37: Live Calendar Sync - Stories 37.2, 37.4
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from .base import Base


def _utc_now():
    """Return current UTC time without timezone info for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class Meeting(Base):
    __tablename__ = "meeting"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False, index=True)
    ends_at = Column(DateTime, nullable=False)
    source = Column(String, nullable=True)
    cancelled_at = Column(DateTime, nullable=True, index=True)  # Soft delete for calendar sync

    # Story 37.4: Override tracking for sync conflict resolution
    local_override = Column(Boolean, default=False, nullable=False)
    calendar_title = Column(String, nullable=True)  # Original value from calendar
    calendar_starts_at = Column(DateTime, nullable=True)
    calendar_ends_at = Column(DateTime, nullable=True)

    # Story 37.5: Multi-calendar support
    calendar_source_id = Column(
        String,
        ForeignKey("calendar_connection.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    @property
    def is_cancelled(self) -> bool:
        """Check if meeting was cancelled/deleted from calendar."""
        return self.cancelled_at is not None

    @property
    def has_conflict(self) -> bool:
        """Check if meeting has local override that conflicts with calendar."""
        if not self.local_override:
            return False
        if self.calendar_title and self.title != self.calendar_title:
            return True
        if self.calendar_starts_at and self.starts_at != self.calendar_starts_at:
            return True
        if self.calendar_ends_at and self.ends_at != self.calendar_ends_at:
            return True
        return False

    def get_conflicts(self) -> dict:
        """Get conflict details if meeting has local override."""
        conflicts = {}
        if not self.local_override:
            return conflicts

        if self.calendar_title and self.title != self.calendar_title:
            conflicts["title"] = {
                "local": self.title,
                "calendar": self.calendar_title,
            }
        if self.calendar_starts_at and self.starts_at != self.calendar_starts_at:
            conflicts["starts_at"] = {
                "local": self.starts_at.isoformat() if self.starts_at else None,
                "calendar": self.calendar_starts_at.isoformat() if self.calendar_starts_at else None,
            }
        if self.calendar_ends_at and self.ends_at != self.calendar_ends_at:
            conflicts["ends_at"] = {
                "local": self.ends_at.isoformat() if self.ends_at else None,
                "calendar": self.calendar_ends_at.isoformat() if self.calendar_ends_at else None,
            }

        return conflicts
