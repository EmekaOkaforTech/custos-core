"""Microsoft Calendar provider using Microsoft Graph API.

Epic 37: Live Calendar Sync - Story 37.1
Fetches real calendar events from Outlook/Microsoft 365 using OAuth tokens.
"""

from datetime import datetime
from typing import Any

import httpx

from .provider import CalendarAttendee, CalendarEvent

# Microsoft Graph API endpoints
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_EVENTS_URL = f"{GRAPH_BASE}/me/calendar/events"


class MicrosoftCalendarProvider:
    """Microsoft Calendar provider using OAuth access token.

    Implements the CalendarProvider protocol for Microsoft 365/Outlook Calendar.
    """

    def __init__(self, access_token: str):
        """Initialize with OAuth access token.

        Args:
            access_token: Valid Microsoft OAuth access token with Calendars.Read scope
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
        # Microsoft Graph uses OData filter syntax
        filter_query = (
            f"start/dateTime ge '{start.isoformat()}Z' and "
            f"end/dateTime le '{end.isoformat()}Z'"
        )
        params = {
            "$filter": filter_query,
            "$orderby": "start/dateTime",
            "$top": 100,
            "$select": "id,subject,start,end,attendees",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    GRAPH_EVENTS_URL,
                    headers=self._headers,
                    params=params,
                )

            if response.status_code != 200:
                return []

            data = response.json()
            events = []

            for item in data.get("value", []):
                event = self._parse_event(item)
                if event:
                    events.append(event)

            return events
        except Exception:
            return []

    def get_event(self, event_id: str) -> CalendarEvent | None:
        """Get a specific calendar event by ID.

        Args:
            event_id: Microsoft Graph event ID

        Returns:
            Calendar event or None if not found
        """
        url = f"{GRAPH_EVENTS_URL}/{event_id}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    url,
                    headers=self._headers,
                    params={"$select": "id,subject,start,end,attendees"},
                )

            if response.status_code != 200:
                return None

            data = response.json()
            return self._parse_event(data)
        except Exception:
            return None

    def list_attendees(self, event_id: str) -> list[CalendarAttendee]:
        """Get attendees for a specific event.

        Args:
            event_id: Microsoft Graph event ID

        Returns:
            List of attendees
        """
        url = f"{GRAPH_EVENTS_URL}/{event_id}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    url,
                    headers=self._headers,
                    params={"$select": "attendees"},
                )

            if response.status_code != 200:
                return []

            data = response.json()
            attendees = []

            for attendee in data.get("attendees", []):
                email_address = attendee.get("emailAddress", {})
                email = email_address.get("address")
                if email:
                    attendees.append(
                        CalendarAttendee(
                            identifier=email,
                            display_name=email_address.get("name"),
                        )
                    )

            return attendees
        except Exception:
            return []

    def _parse_event(self, item: dict[str, Any]) -> CalendarEvent | None:
        """Parse a Microsoft Graph API event item.

        Args:
            item: Event data from Microsoft Graph API

        Returns:
            CalendarEvent or None if parsing fails
        """
        event_id = item.get("id")
        title = item.get("subject", "Untitled Event")

        start_data = item.get("start", {})
        end_data = item.get("end", {})

        start_str = start_data.get("dateTime")
        end_str = end_data.get("dateTime")

        if not event_id or not start_str or not end_str:
            return None

        try:
            # Microsoft Graph returns ISO format without Z, assumes UTC
            # Format: 2024-01-15T09:00:00.0000000
            starts_at = datetime.fromisoformat(start_str.split(".")[0])
            ends_at = datetime.fromisoformat(end_str.split(".")[0])

            return CalendarEvent(
                event_id=event_id,
                title=title,
                starts_at=starts_at,
                ends_at=ends_at,
            )
        except ValueError:
            return None
