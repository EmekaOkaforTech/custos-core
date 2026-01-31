"""Google Calendar provider using Google Calendar API.

Epic 37: Live Calendar Sync - Story 37.1
Fetches real calendar events from Google Calendar using OAuth tokens.
"""

from datetime import datetime
from typing import Any

import httpx

from .provider import CalendarAttendee, CalendarEvent

# Google Calendar API endpoints
GOOGLE_CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
GOOGLE_EVENTS_URL = f"{GOOGLE_CALENDAR_BASE}/calendars/primary/events"


class GoogleCalendarProvider:
    """Google Calendar provider using OAuth access token.

    Implements the CalendarProvider protocol for Google Calendar.
    """

    def __init__(self, access_token: str):
        """Initialize with OAuth access token.

        Args:
            access_token: Valid Google OAuth access token with calendar scope
        """
        self.access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """List calendar events in the given time range.

        Args:
            start: Start of time range (UTC)
            end: End of time range (UTC)

        Returns:
            List of calendar events
        """
        params = {
            "timeMin": start.isoformat() + "Z",
            "timeMax": end.isoformat() + "Z",
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 100,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    GOOGLE_EVENTS_URL,
                    headers=self._headers,
                    params=params,
                )

            if response.status_code != 200:
                return []

            data = response.json()
            events = []

            for item in data.get("items", []):
                event = self._parse_event(item)
                if event:
                    events.append(event)

            return events
        except Exception:
            return []

    def get_event(self, event_id: str) -> CalendarEvent | None:
        """Get a specific calendar event by ID.

        Args:
            event_id: Google Calendar event ID

        Returns:
            Calendar event or None if not found
        """
        url = f"{GOOGLE_EVENTS_URL}/{event_id}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=self._headers)

            if response.status_code != 200:
                return None

            data = response.json()
            return self._parse_event(data)
        except Exception:
            return None

    def list_attendees(self, event_id: str) -> list[CalendarAttendee]:
        """Get attendees for a specific event.

        Args:
            event_id: Google Calendar event ID

        Returns:
            List of attendees
        """
        url = f"{GOOGLE_EVENTS_URL}/{event_id}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=self._headers)

            if response.status_code != 200:
                return []

            data = response.json()
            attendees = []

            for attendee in data.get("attendees", []):
                email = attendee.get("email")
                if email:
                    attendees.append(
                        CalendarAttendee(
                            identifier=email,
                            display_name=attendee.get("displayName"),
                        )
                    )

            return attendees
        except Exception:
            return []

    def _parse_event(self, item: dict[str, Any]) -> CalendarEvent | None:
        """Parse a Google Calendar API event item.

        Args:
            item: Event data from Google Calendar API

        Returns:
            CalendarEvent or None if parsing fails
        """
        event_id = item.get("id")
        title = item.get("summary", "Untitled Event")

        # Parse start time (can be date or dateTime)
        start_data = item.get("start", {})
        end_data = item.get("end", {})

        start_str = start_data.get("dateTime") or start_data.get("date")
        end_str = end_data.get("dateTime") or end_data.get("date")

        if not event_id or not start_str or not end_str:
            return None

        try:
            # Handle both dateTime (with timezone) and date (all-day)
            if "T" in start_str:
                # dateTime format: 2024-01-15T09:00:00-05:00
                starts_at = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                ends_at = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                # Convert to UTC for storage
                starts_at = starts_at.replace(tzinfo=None)
                ends_at = ends_at.replace(tzinfo=None)
            else:
                # date format: 2024-01-15 (all-day event)
                starts_at = datetime.fromisoformat(start_str)
                ends_at = datetime.fromisoformat(end_str)

            return CalendarEvent(
                event_id=event_id,
                title=title,
                starts_at=starts_at,
                ends_at=ends_at,
            )
        except ValueError:
            return None
