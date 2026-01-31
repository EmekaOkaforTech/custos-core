"""Tests for sync conflict resolution - Epic 37 Story 37.4."""

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


class TestMeetingOverrideTracking:
    """Tests for local override tracking on meetings."""

    def test_update_meeting_sets_override_flag(self, client, test_db):
        """Editing a calendar meeting title sets local_override flag."""
        # Create calendar meeting
        meeting = Meeting(
            id="m_cal_test123",
            title="Original Title",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="calendar",
        )
        test_db.add(meeting)
        test_db.commit()

        # Update the meeting title
        response = client.patch(
            "/api/meetings/m_cal_test123",
            json={"title": "My Custom Title"},
        )
        assert response.status_code == 200

        # Verify override flag is set
        test_db.refresh(meeting)
        assert meeting.local_override is True
        assert meeting.calendar_title == "Original Title"
        assert meeting.title == "My Custom Title"

    def test_update_manual_meeting_no_override(self, client, test_db):
        """Editing a manual meeting does not set override flag."""
        meeting = Meeting(
            id="m_manual_test",
            title="Manual Meeting",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="manual",
        )
        test_db.add(meeting)
        test_db.commit()

        response = client.patch(
            "/api/meetings/m_manual_test",
            json={"title": "Updated Manual"},
        )
        assert response.status_code == 200

        test_db.refresh(meeting)
        assert meeting.local_override is False
        assert meeting.calendar_title is None

    def test_has_conflict_property(self, test_db):
        """Meeting.has_conflict returns True when override differs from calendar."""
        meeting = Meeting(
            id="m_cal_conflict",
            title="Local Title",
            starts_at=_utc_now(),
            ends_at=_utc_now() + timedelta(hours=1),
            source="calendar",
            local_override=True,
            calendar_title="Calendar Title",
        )
        test_db.add(meeting)
        test_db.commit()

        assert meeting.has_conflict is True

    def test_has_conflict_no_override(self, test_db):
        """Meeting without local_override has no conflict."""
        meeting = Meeting(
            id="m_cal_no_conflict",
            title="Same Title",
            starts_at=_utc_now(),
            ends_at=_utc_now() + timedelta(hours=1),
            source="calendar",
            local_override=False,
        )
        test_db.add(meeting)
        test_db.commit()

        assert meeting.has_conflict is False

    def test_get_conflicts_returns_diff(self, test_db):
        """Meeting.get_conflicts returns detailed diff."""
        now = _utc_now()
        calendar_start = now + timedelta(hours=1)
        local_start = now + timedelta(hours=2)

        meeting = Meeting(
            id="m_cal_detailed",
            title="Local Title",
            starts_at=local_start,
            ends_at=now + timedelta(hours=3),
            source="calendar",
            local_override=True,
            calendar_title="Calendar Title",
            calendar_starts_at=calendar_start,
        )
        test_db.add(meeting)
        test_db.commit()

        conflicts = meeting.get_conflicts()
        assert "title" in conflicts
        assert conflicts["title"]["local"] == "Local Title"
        assert conflicts["title"]["calendar"] == "Calendar Title"
        assert "starts_at" in conflicts


class TestSyncWithOverrides:
    """Tests for calendar sync respecting local overrides."""

    def test_sync_skips_overridden_meeting(self, test_db):
        """Calendar sync stores calendar values but doesn't update overridden meeting."""
        from app.calendar.demo_provider import DemoCalendarProvider
        from app.calendar.ingest import ingest_calendar

        os.environ["CUSTOS_CALENDAR_ENABLED"] = "1"

        # Create existing meeting with local override
        meeting = Meeting(
            id="m_cal_demo_001",  # Matches demo provider event ID
            title="My Custom Title",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="calendar",
            local_override=True,
            calendar_title="Old Calendar Title",
        )
        test_db.add(meeting)

        conn = CalendarConnection(
            id="conn_test",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="demo-token",
            enabled=True,
        )
        test_db.add(conn)
        test_db.commit()

        provider = DemoCalendarProvider()
        result = ingest_calendar(provider, test_db)

        assert result["status"] == "ok"

        # Verify local title was preserved
        test_db.refresh(meeting)
        assert meeting.title == "My Custom Title"
        assert meeting.local_override is True
        # Calendar values should be updated
        assert meeting.calendar_title is not None


class TestForceRefresh:
    """Tests for force-refresh endpoint."""

    def test_force_refresh_restores_calendar_values(self, client, test_db):
        """Force refresh clears local override and restores calendar values."""
        now = _utc_now()
        calendar_start = now + timedelta(hours=1)
        calendar_end = now + timedelta(hours=2)

        meeting = Meeting(
            id="m_cal_refresh",
            title="Local Override Title",
            starts_at=now + timedelta(hours=3),  # Different from calendar
            ends_at=now + timedelta(hours=4),
            source="calendar",
            local_override=True,
            calendar_title="Original Calendar Title",
            calendar_starts_at=calendar_start,
            calendar_ends_at=calendar_end,
        )
        test_db.add(meeting)
        test_db.commit()

        response = client.post("/api/meetings/m_cal_refresh/force-refresh")
        assert response.status_code == 200

        data = response.json()
        assert data["refreshed"] is True
        assert data["meeting"]["title"] == "Original Calendar Title"

        # Verify database state
        test_db.refresh(meeting)
        assert meeting.local_override is False
        assert meeting.title == "Original Calendar Title"
        assert meeting.starts_at == calendar_start
        assert meeting.ends_at == calendar_end
        assert meeting.calendar_title is None

    def test_force_refresh_manual_meeting_fails(self, client, test_db):
        """Force refresh on manual meeting returns error."""
        meeting = Meeting(
            id="m_manual_refresh",
            title="Manual Meeting",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="manual",
        )
        test_db.add(meeting)
        test_db.commit()

        response = client.post("/api/meetings/m_manual_refresh/force-refresh")
        assert response.status_code == 400
        assert "calendar meetings" in response.json()["detail"]

    def test_force_refresh_no_override(self, client, test_db):
        """Force refresh on meeting without override returns no change."""
        meeting = Meeting(
            id="m_cal_no_override",
            title="Calendar Title",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="calendar",
            local_override=False,
        )
        test_db.add(meeting)
        test_db.commit()

        response = client.post("/api/meetings/m_cal_no_override/force-refresh")
        assert response.status_code == 200

        data = response.json()
        assert data["refreshed"] is False

    def test_force_refresh_not_found(self, client, test_db):
        """Force refresh on non-existent meeting returns 404."""
        response = client.post("/api/meetings/m_nonexistent/force-refresh")
        assert response.status_code == 404


class TestConflictsEndpoint:
    """Tests for GET /api/calendar/conflicts endpoint."""

    def test_no_conflicts_returns_empty(self, client, test_db):
        """No conflicts returns empty list."""
        response = client.get("/api/calendar/conflicts")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 0
        assert data["conflicts"] == []

    def test_lists_conflicting_meetings(self, client, test_db):
        """Returns meetings with local overrides that conflict."""
        meeting = Meeting(
            id="m_cal_with_conflict",
            title="Local Title",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="calendar",
            local_override=True,
            calendar_title="Calendar Title",
        )
        test_db.add(meeting)
        test_db.commit()

        response = client.get("/api/calendar/conflicts")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 1
        assert data["conflicts"][0]["meeting_id"] == "m_cal_with_conflict"
        assert "title" in data["conflicts"][0]["conflicts"]

    def test_excludes_cancelled_meetings(self, client, test_db):
        """Cancelled meetings are not included in conflicts."""
        meeting = Meeting(
            id="m_cal_cancelled_conflict",
            title="Local Title",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="calendar",
            local_override=True,
            calendar_title="Calendar Title",
            cancelled_at=_utc_now(),
        )
        test_db.add(meeting)
        test_db.commit()

        response = client.get("/api/calendar/conflicts")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 0

    def test_excludes_non_conflicting_overrides(self, client, test_db):
        """Overrides without actual conflicts are not returned."""
        meeting = Meeting(
            id="m_cal_override_no_diff",
            title="Same Title",
            starts_at=_utc_now() + timedelta(hours=1),
            ends_at=_utc_now() + timedelta(hours=2),
            source="calendar",
            local_override=True,
            calendar_title="Same Title",  # Same as local
        )
        test_db.add(meeting)
        test_db.commit()

        response = client.get("/api/calendar/conflicts")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 0
