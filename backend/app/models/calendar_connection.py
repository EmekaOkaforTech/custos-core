"""Calendar connection model for OAuth calendar integration.

Epic 37: Live Calendar Sync - Story 37.1
Stores OAuth tokens and connection metadata for Google Calendar and Microsoft Outlook.
"""

from datetime import datetime, timedelta, UTC

from sqlalchemy import Boolean, Column, DateTime, String, Text

from .base import Base


def _utc_now():
    """Return current UTC time without timezone info for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class CalendarConnection(Base):
    """Stores calendar provider connection with OAuth tokens.

    Tokens are stored encrypted at rest via SQLCipher database encryption.
    Story 37.5: Supports multiple connections (work + personal calendars).
    """

    __tablename__ = "calendar_connection"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)  # Story 37.5: Display name (e.g., "Work", "Personal")
    provider = Column(String, nullable=False)  # "google" | "microsoft" | "demo"
    scopes = Column(Text, nullable=False)  # JSON array of OAuth scopes
    token = Column(Text, nullable=False)  # Access token (encrypted at rest)
    refresh_token = Column(Text, nullable=True)  # Refresh token (encrypted at rest)
    token_expires_at = Column(DateTime, nullable=True)  # When access token expires
    last_refresh_at = Column(DateTime, nullable=True)  # Last token refresh timestamp
    provider_user_id = Column(String, nullable=True)  # User identifier from provider
    enabled = Column(Boolean, default=False, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)  # Last successful calendar sync
    sync_error = Column(String, nullable=True)  # Last sync error message
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    def is_token_expired(self) -> bool:
        """Check if access token is expired or about to expire (within 5 min)."""
        if self.token_expires_at is None:
            return False
        buffer = timedelta(minutes=5)
        return _utc_now() >= (self.token_expires_at - buffer)

    def needs_refresh(self) -> bool:
        """Check if token needs refresh (expired and has refresh token)."""
        return self.is_token_expired() and self.refresh_token is not None
