"""Calendar sync runner - background polling service.

Epic 37: Live Calendar Sync - Story 37.2
Polls connected calendar providers and syncs events to local database.
"""

import logging
import time

from sqlalchemy.orm import Session

from app.calendar.demo_provider import DemoCalendarProvider
from app.calendar.google_provider import GoogleCalendarProvider
from app.calendar.ingest import ingest_calendar
from app.calendar.microsoft_provider import MicrosoftCalendarProvider
from app.calendar.provider import CalendarProvider
from app.db import SessionLocal
from app.models.calendar_connection import CalendarConnection
from app.oauth.token_manager import TokenManager
from app.settings import get_calendar_enabled, get_calendar_poll_seconds, get_env

logger = logging.getLogger(__name__)


def get_calendar_provider(db: Session) -> CalendarProvider | None:
    """Get appropriate calendar provider based on connection.

    Returns the configured calendar provider with a valid access token,
    or None if no connection exists or tokens are invalid.
    """
    connection = (
        db.query(CalendarConnection)
        .filter(CalendarConnection.enabled.is_(True))
        .first()
    )

    if not connection:
        # In dev mode, fall back to demo provider if enabled
        if get_env() == "dev" and get_calendar_enabled():
            logger.debug("No OAuth connection, using demo provider in dev mode")
            return DemoCalendarProvider()
        return None

    if connection.provider == "demo":
        return DemoCalendarProvider()

    # OAuth provider - get valid token via TokenManager
    try:
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(connection)

        if connection.provider == "google":
            logger.debug("Using Google Calendar provider")
            return GoogleCalendarProvider(access_token)
        elif connection.provider == "microsoft":
            logger.debug("Using Microsoft Calendar provider")
            return MicrosoftCalendarProvider(access_token)
        else:
            logger.warning("Unknown provider: %s", connection.provider)
            return None

    except Exception as e:
        logger.error("Failed to get calendar provider: %s", str(e))
        # Update connection with sync error
        connection.sync_error = str(e)
        db.commit()
        return None


def run_once() -> dict:
    """Run a single calendar sync cycle for all enabled connections.

    Story 37.5: Processes each enabled connection independently.

    Returns:
        dict with sync result status for all connections
    """
    if not get_calendar_enabled():
        return {"status": "disabled"}

    session = SessionLocal()
    try:
        # Get all enabled connections
        connections = (
            session.query(CalendarConnection)
            .filter(CalendarConnection.enabled.is_(True))
            .all()
        )

        if not connections:
            # Fallback to dev mode demo provider
            if get_env() == "dev":
                logger.debug("No connections, using demo provider in dev mode")
                provider = DemoCalendarProvider()
                result = ingest_calendar(provider, session)
                return result
            logger.debug("No calendar connections available")
            return {"status": "no_connection"}

        # Process each connection independently
        results = []
        for connection in connections:
            try:
                provider = get_calendar_provider_for_connection(connection, session)
                if provider:
                    result = ingest_calendar(provider, session, connection_id=connection.id)
                    results.append({
                        "connection_id": connection.id,
                        "connection_name": connection.name,
                        "provider": connection.provider,
                        **result,
                    })
            except Exception as e:
                logger.error("Sync failed for connection %s: %s", connection.id, str(e))
                results.append({
                    "connection_id": connection.id,
                    "connection_name": connection.name,
                    "provider": connection.provider,
                    "status": "error",
                    "error": str(e),
                })

        return {
            "status": "ok",
            "connections": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error("Calendar sync failed: %s", str(e))
        return {"status": "error", "error": str(e)}
    finally:
        session.close()


def get_calendar_provider_for_connection(
    connection: CalendarConnection, db: Session
) -> CalendarProvider | None:
    """Get calendar provider for a specific connection.

    Story 37.5: Handles provider instantiation for multi-calendar support.
    """
    if connection.provider == "demo":
        return DemoCalendarProvider()

    # OAuth provider - get valid token via TokenManager
    try:
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(connection)

        if connection.provider == "google":
            logger.debug("Using Google Calendar provider for connection %s", connection.id)
            return GoogleCalendarProvider(access_token)
        elif connection.provider == "microsoft":
            logger.debug("Using Microsoft Calendar provider for connection %s", connection.id)
            return MicrosoftCalendarProvider(access_token)
        else:
            logger.warning("Unknown provider: %s", connection.provider)
            return None

    except Exception as e:
        logger.error("Failed to get provider for connection %s: %s", connection.id, str(e))
        connection.sync_error = str(e)
        db.commit()
        return None


def run_forever():
    """Run calendar sync in infinite loop with configured poll interval."""
    poll_seconds = get_calendar_poll_seconds()
    logger.info("Starting calendar runner with %d second poll interval", poll_seconds)

    while True:
        try:
            result = run_once()
            logger.debug("Sync result: %s", result)
        except Exception as e:
            logger.error("Unexpected error in sync loop: %s", str(e))
        time.sleep(poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
