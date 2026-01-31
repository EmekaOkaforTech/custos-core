"""
Datetime utilities for Custos Core.

Provides consistent UTC datetime handling without deprecation warnings.
All datetimes in the system are stored as naive UTC for SQLite compatibility.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Return the current UTC time as a naive datetime.

    This replaces the deprecated datetime.utcnow() with the recommended
    approach of using timezone-aware datetimes and converting to naive.

    Returns:
        Naive datetime representing the current UTC time.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
