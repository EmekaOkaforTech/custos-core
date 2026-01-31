"""Tests for multi-calendar support - Epic 37 Story 37.5."""

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

# Ensure test environment
os.environ.setdefault("CUSTOS_ALLOW_PLAINTEXT_DB", "1")
os.environ.setdefault("CUSTOS_DATABASE_KEY", "test-key")

from app.models.calendar_connection import CalendarConnection
from app.models.meeting import Meeting


@pytest.fixture
def client(test_app):
    """Test client with fresh database."""
    return TestClient(test_app)


def _utc_now():
    """Return current UTC time without timezone info."""
    return datetime.now(UTC).replace(tzinfo=None)


class TestMultipleConnections:
    """Tests for multiple calendar connections."""

    def test_list_connections_empty(self, client, test_db):
        """List connections returns empty when none exist."""
        response = client.get("/api/calendar/connections")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 0
        assert data["connections"] == []

    def test_list_multiple_connections(self, client, test_db):
        """List shows all configured connections."""
        conn1 = CalendarConnection(
            id="cal_work",
            name="Work Calendar",
            provider="google",
            scopes=json.dumps(["read"]),
            token="token1",
            enabled=True,
        )
        conn2 = CalendarConnection(
            id="cal_personal",
            name="Personal Calendar",
            provider="microsoft",
            scopes=json.dumps(["read"]),
            token="token2",
            enabled=False,
        )
        test_db.add_all([conn1, conn2])
        test_db.commit()

        response = client.get("/api/calendar/connections")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 2
        assert len(data["connections"]) == 2

        # Check first connection
        work = next(c for c in data["connections"] if c["id"] == "cal_work")
        assert work["name"] == "Work Calendar"
        assert work["provider"] == "google"
        assert work["enabled"] is True

    def test_update_connection_name(self, client, test_db):
        """Update connection name via PATCH."""
        conn = CalendarConnection(
            id="cal_test",
            name="Old Name",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token",
            enabled=True,
        )
        test_db.add(conn)
        test_db.commit()

        response = client.patch(
            "/api/calendar/connections/cal_test",
            json={"name": "New Name"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "New Name"

        test_db.refresh(conn)
        assert conn.name == "New Name"

    def test_update_connection_enabled(self, client, test_db):
        """Update connection enabled status via PATCH."""
        conn = CalendarConnection(
            id="cal_toggle",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token",
            enabled=True,
        )
        test_db.add(conn)
        test_db.commit()

        response = client.patch(
            "/api/calendar/connections/cal_toggle",
            json={"enabled": False},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["enabled"] is False

    def test_delete_specific_connection(self, client, test_db):
        """Delete a specific connection."""
        conn1 = CalendarConnection(
            id="cal_keep",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token",
            enabled=True,
        )
        conn2 = CalendarConnection(
            id="cal_delete",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token",
            enabled=True,
        )
        test_db.add_all([conn1, conn2])
        test_db.commit()

        response = client.delete("/api/calendar/connections/cal_delete")
        assert response.status_code == 200

        # Verify cal_keep still exists
        assert test_db.get(CalendarConnection, "cal_keep") is not None
        assert test_db.get(CalendarConnection, "cal_delete") is None

    def test_delete_nonexistent_connection(self, client, test_db):
        """Delete nonexistent connection returns 404."""
        response = client.delete("/api/calendar/connections/nonexistent")
        assert response.status_code == 404


class TestMeetingSourceTagging:
    """Tests for meeting calendar source tracking."""

    def test_meeting_stores_calendar_source_id(self, test_db):
        """Meeting has calendar_source_id field."""
        conn = CalendarConnection(
            id="cal_source",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token",
            enabled=True,
        )
        test_db.add(conn)

        meeting = Meeting(
            id="m_with_source",
            title="Test Meeting",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="calendar",
            calendar_source_id="cal_source",
        )
        test_db.add(meeting)
        test_db.commit()

        assert meeting.calendar_source_id == "cal_source"

    def test_ingest_sets_calendar_source_id(self, test_db):
        """Calendar ingest sets calendar_source_id on meetings."""
        from app.calendar.demo_provider import DemoCalendarProvider
        from app.calendar.ingest import ingest_calendar

        os.environ["CUSTOS_CALENDAR_ENABLED"] = "1"

        conn = CalendarConnection(
            id="cal_ingest_test",
            name="Test Calendar",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="demo-token",
            enabled=True,
        )
        test_db.add(conn)
        test_db.commit()

        provider = DemoCalendarProvider()
        result = ingest_calendar(provider, test_db, connection_id="cal_ingest_test")

        assert result["status"] == "ok"

        # Check that meetings have the calendar_source_id set
        meetings = test_db.query(Meeting).filter(
            Meeting.calendar_source_id == "cal_ingest_test"
        ).all()
        assert len(meetings) > 0


class TestBriefingFilters:
    """Tests for briefing calendar source filtering."""

    def test_today_briefing_filter_by_source(self, client, test_db):
        """Today briefing can filter by calendar source."""
        now = _utc_now()
        today_start = datetime(now.year, now.month, now.day)

        # Create meeting from work calendar
        meeting1 = Meeting(
            id="m_work_today",
            title="Work Meeting",
            starts_at=today_start + timedelta(hours=10),
            ends_at=today_start + timedelta(hours=11),
            source="calendar",
            calendar_source_id="cal_work",
        )
        # Create meeting from personal calendar
        meeting2 = Meeting(
            id="m_personal_today",
            title="Personal Meeting",
            starts_at=today_start + timedelta(hours=14),
            ends_at=today_start + timedelta(hours=15),
            source="calendar",
            calendar_source_id="cal_personal",
        )
        test_db.add_all([meeting1, meeting2])
        test_db.commit()

        # Without filter - returns both
        response = client.get("/api/briefings/today")
        assert response.status_code == 200
        data = response.json()
        assert len(data["meetings"]) == 2

        # With filter - returns only work
        response = client.get("/api/briefings/today?calendar_source=cal_work")
        assert response.status_code == 200
        data = response.json()
        assert len(data["meetings"]) == 1
        assert data["meetings"][0]["id"] == "m_work_today"
        assert data["meetings"][0]["calendar_source_id"] == "cal_work"

    def test_next_briefing_filter_by_source(self, client, test_db):
        """Next briefing can filter by calendar source."""
        now = _utc_now()

        meeting1 = Meeting(
            id="m_work_next",
            title="Work Meeting",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            source="calendar",
            calendar_source_id="cal_work",
        )
        meeting2 = Meeting(
            id="m_personal_next",
            title="Personal Meeting",
            starts_at=now + timedelta(hours=2),
            ends_at=now + timedelta(hours=3),
            source="calendar",
            calendar_source_id="cal_personal",
        )
        test_db.add_all([meeting1, meeting2])
        test_db.commit()

        # Filter by personal - skips work meeting
        response = client.get("/api/briefings/next?calendar_source=cal_personal")
        assert response.status_code == 200
        data = response.json()
        assert data["meeting"]["id"] == "m_personal_next"


class TestRunnerMultipleConnections:
    """Tests for runner processing multiple connections."""

    def test_runner_processes_all_enabled_connections(self, test_db):
        """Runner processes each enabled connection."""
        from app.calendar.runner import run_once

        os.environ["CUSTOS_CALENDAR_ENABLED"] = "1"

        conn1 = CalendarConnection(
            id="cal_enabled1",
            name="Enabled 1",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token1",
            enabled=True,
        )
        conn2 = CalendarConnection(
            id="cal_enabled2",
            name="Enabled 2",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token2",
            enabled=True,
        )
        conn3 = CalendarConnection(
            id="cal_disabled",
            name="Disabled",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="token3",
            enabled=False,
        )
        test_db.add_all([conn1, conn2, conn3])
        test_db.commit()
        test_db.close()

        result = run_once()

        assert result["status"] == "ok"
        assert result["connections"] == 2  # Only enabled connections processed

        # Verify both connections have results
        connection_ids = [r["connection_id"] for r in result["results"]]
        assert "cal_enabled1" in connection_ids
        assert "cal_enabled2" in connection_ids
        assert "cal_disabled" not in connection_ids
