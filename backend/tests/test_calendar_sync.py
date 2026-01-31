"""Tests for calendar sync functionality - Epic 37 Story 37.2."""

import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Ensure test environment
os.environ.setdefault("CUSTOS_ALLOW_PLAINTEXT_DB", "1")
os.environ.setdefault("CUSTOS_DATABASE_KEY", "test-key")

from fastapi.testclient import TestClient

from app.calendar.ingest import ingest_calendar
from app.calendar.provider import CalendarAttendee, CalendarEvent
from app.calendar.runner import get_calendar_provider, run_once
from app.main import app
from app.models.calendar_connection import CalendarConnection
from app.models.meeting import Meeting


@pytest.fixture
def client(test_app):
    """Test client with fresh database."""
    return TestClient(test_app)


def _utc_now():
    """Return current UTC time without timezone info."""
    return datetime.now(UTC).replace(tzinfo=None)


class TestCalendarRunner:
    """Tests for calendar runner OAuth integration."""

    def test_get_provider_no_connection(self, test_db):
        """Returns None when no connection exists."""
        with patch("app.calendar.runner.get_calendar_enabled", return_value=True):
            with patch("app.calendar.runner.get_env", return_value="prod"):
                provider = get_calendar_provider(test_db)
        assert provider is None

    def test_get_provider_demo_connection(self, test_db):
        """Returns DemoCalendarProvider for demo connections."""
        connection = CalendarConnection(
            id="cal_demo123",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="demo_token",
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        provider = get_calendar_provider(test_db)
        assert provider is not None
        assert provider.__class__.__name__ == "DemoCalendarProvider"

    def test_get_provider_google_oauth(self, test_db):
        """Returns GoogleCalendarProvider for Google OAuth connections."""
        connection = CalendarConnection(
            id="cal_google123",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="access_token",
            refresh_token="refresh_token",
            token_expires_at=_utc_now() + timedelta(hours=1),
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        mock_provider = MagicMock()
        with patch("app.calendar.runner.TokenManager") as mock_tm:
            mock_tm.return_value.get_valid_token.return_value = "valid_token"
            with patch("app.calendar.runner.GoogleCalendarProvider") as mock_google:
                mock_google.return_value = mock_provider
                provider = get_calendar_provider(test_db)

        assert provider is mock_provider
        mock_google.assert_called_once_with("valid_token")

    def test_get_provider_microsoft_oauth(self, test_db):
        """Returns MicrosoftCalendarProvider for Microsoft OAuth connections."""
        connection = CalendarConnection(
            id="cal_microsoft123",
            provider="microsoft",
            scopes=json.dumps(["Calendars.Read"]),
            token="access_token",
            refresh_token="refresh_token",
            token_expires_at=_utc_now() + timedelta(hours=1),
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        mock_provider = MagicMock()
        with patch("app.calendar.runner.TokenManager") as mock_tm:
            mock_tm.return_value.get_valid_token.return_value = "valid_token"
            with patch("app.calendar.runner.MicrosoftCalendarProvider") as mock_ms:
                mock_ms.return_value = mock_provider
                provider = get_calendar_provider(test_db)

        assert provider is mock_provider
        mock_ms.assert_called_once_with("valid_token")

    def test_run_once_disabled(self):
        """Returns disabled status when calendar is disabled."""
        with patch("app.calendar.runner.get_calendar_enabled", return_value=False):
            result = run_once()
        assert result == {"status": "disabled"}


class TestCalendarIngest:
    """Tests for calendar ingestion with deletion handling."""

    def test_ingest_creates_meetings(self, test_db):
        """Creates Meeting records from calendar events."""
        mock_provider = MagicMock()
        mock_provider.list_events.return_value = [
            CalendarEvent(
                event_id="event1",
                title="Test Meeting",
                starts_at=_utc_now() + timedelta(hours=1),
                ends_at=_utc_now() + timedelta(hours=2),
            )
        ]
        mock_provider.list_attendees.return_value = []

        with patch("app.calendar.ingest.get_calendar_enabled", return_value=True):
            with patch("app.calendar.ingest.mark_success"):
                result = ingest_calendar(mock_provider, test_db)

        assert result["status"] == "ok"
        assert result["events"] == 1

        meeting = test_db.query(Meeting).filter(Meeting.id == "m_cal_event1").first()
        assert meeting is not None
        assert meeting.title == "Test Meeting"
        assert meeting.source == "calendar"

    def test_ingest_updates_existing_meetings(self, test_db):
        """Updates existing Meeting records when events change."""
        # Create existing meeting
        meeting = Meeting(
            id="m_cal_event1",
            title="Old Title",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="calendar",
        )
        test_db.add(meeting)
        test_db.commit()

        mock_provider = MagicMock()
        mock_provider.list_events.return_value = [
            CalendarEvent(
                event_id="event1",
                title="New Title",
                starts_at=_utc_now() + timedelta(hours=2),
                ends_at=_utc_now() + timedelta(hours=3),
            )
        ]
        mock_provider.list_attendees.return_value = []

        with patch("app.calendar.ingest.get_calendar_enabled", return_value=True):
            with patch("app.calendar.ingest.mark_success"):
                result = ingest_calendar(mock_provider, test_db)

        assert result["status"] == "ok"

        test_db.refresh(meeting)
        assert meeting.title == "New Title"

    def test_ingest_marks_deleted_meetings_as_cancelled(self, test_db):
        """Marks meetings as cancelled when removed from calendar."""
        now = _utc_now()
        # Create existing meeting within sync range
        meeting = Meeting(
            id="m_cal_deleted_event",
            title="Deleted Meeting",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            source="calendar",
        )
        test_db.add(meeting)
        test_db.commit()

        # Sync returns no events (meeting was deleted)
        mock_provider = MagicMock()
        mock_provider.list_events.return_value = []
        mock_provider.list_attendees.return_value = []

        with patch("app.calendar.ingest.get_calendar_enabled", return_value=True):
            with patch("app.calendar.ingest.mark_success"):
                result = ingest_calendar(mock_provider, test_db)

        assert result["status"] == "ok"
        assert result["cancelled"] == 1

        test_db.refresh(meeting)
        assert meeting.cancelled_at is not None

    def test_ingest_restores_cancelled_meeting_if_reappears(self, test_db):
        """Restores cancelled meeting if it reappears in calendar."""
        now = _utc_now()
        # Create cancelled meeting
        meeting = Meeting(
            id="m_cal_restored_event",
            title="Restored Meeting",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            source="calendar",
            cancelled_at=now - timedelta(hours=1),
        )
        test_db.add(meeting)
        test_db.commit()

        # Event reappears in calendar
        mock_provider = MagicMock()
        mock_provider.list_events.return_value = [
            CalendarEvent(
                event_id="restored_event",
                title="Restored Meeting",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=2),
            )
        ]
        mock_provider.list_attendees.return_value = []

        with patch("app.calendar.ingest.get_calendar_enabled", return_value=True):
            with patch("app.calendar.ingest.mark_success"):
                result = ingest_calendar(mock_provider, test_db)

        assert result["status"] == "ok"

        test_db.refresh(meeting)
        assert meeting.cancelled_at is None  # Restored

    def test_ingest_updates_connection_last_sync(self, test_db):
        """Updates CalendarConnection.last_sync_at after successful sync."""
        connection = CalendarConnection(
            id="cal_test123",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token",
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        mock_provider = MagicMock()
        mock_provider.list_events.return_value = []
        mock_provider.list_attendees.return_value = []

        with patch("app.calendar.ingest.get_calendar_enabled", return_value=True):
            with patch("app.calendar.ingest.mark_success"):
                ingest_calendar(mock_provider, test_db)

        test_db.refresh(connection)
        assert connection.last_sync_at is not None
        assert connection.sync_error is None

    def test_ingest_records_sync_error(self, test_db):
        """Records sync error in CalendarConnection on failure."""
        connection = CalendarConnection(
            id="cal_error_test",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token",
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        mock_provider = MagicMock()
        mock_provider.list_events.side_effect = Exception("API Error")

        with patch("app.calendar.ingest.get_calendar_enabled", return_value=True):
            with patch("app.calendar.ingest.mark_attempt"):
                result = ingest_calendar(mock_provider, test_db)

        assert result["status"] == "failed"
        assert "API Error" in result.get("error", "")

        test_db.refresh(connection)
        assert connection.sync_error == "API Error"


class TestCalendarConnectionAPI:
    """Tests for calendar connection API sync status fields."""

    def test_connection_includes_sync_fields(self, client, test_db):
        """GET /api/calendar/connection includes sync tracking fields."""
        now = _utc_now()
        connection = CalendarConnection(
            id="cal_test123",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="access_token",
            enabled=True,
            last_sync_at=now - timedelta(minutes=5),
            sync_error=None,
        )
        test_db.add(connection)
        test_db.commit()

        response = client.get("/api/calendar/connection")
        assert response.status_code == 200

        data = response.json()
        assert data["connected"] is True
        assert data["provider"] == "google"
        assert data["last_sync_at"] is not None
        assert data["sync_error"] is None

    def test_connection_includes_sync_error(self, client, test_db):
        """GET /api/calendar/connection includes sync_error when present."""
        connection = CalendarConnection(
            id="cal_error_test",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="access_token",
            enabled=True,
            sync_error="Token expired",
        )
        test_db.add(connection)
        test_db.commit()

        response = client.get("/api/calendar/connection")
        assert response.status_code == 200

        data = response.json()
        assert data["sync_error"] == "Token expired"


class TestManualSyncTrigger:
    """Tests for manual sync trigger API endpoint."""

    def test_manual_sync_trigger(self, client, test_db):
        """POST /api/calendar/ingest triggers manual sync."""
        # Create a demo connection
        connection = CalendarConnection(
            id="cal_manual_test",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="demo_token",
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        with patch("app.calendar.ingest.get_calendar_enabled", return_value=True):
            with patch("app.calendar.ingest.mark_success"):
                response = client.post("/api/calendar/ingest")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "events" in data

    def test_manual_sync_updates_last_sync_at(self, client, test_db):
        """Manual sync updates last_sync_at timestamp."""
        connection = CalendarConnection(
            id="cal_sync_test",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="demo_token",
            enabled=True,
            last_sync_at=None,
        )
        test_db.add(connection)
        test_db.commit()

        with patch("app.calendar.ingest.get_calendar_enabled", return_value=True):
            with patch("app.calendar.ingest.mark_success"):
                response = client.post("/api/calendar/ingest")

        assert response.status_code == 200

        test_db.refresh(connection)
        assert connection.last_sync_at is not None


class TestMeetingCancellation:
    """Tests for meeting cancellation model."""

    def test_meeting_is_cancelled_property(self):
        """Meeting.is_cancelled returns correct value."""
        meeting = Meeting(
            id="m_test",
            title="Test",
            starts_at=_utc_now(),
            ends_at=_utc_now() + timedelta(hours=1),
            source="calendar",
        )
        assert meeting.is_cancelled is False

        meeting.cancelled_at = _utc_now()
        assert meeting.is_cancelled is True
