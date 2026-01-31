from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import Session

from app.calendar.ingest import ingest_calendar
from app.calendar.status import mark_attempt
from app.db import add_audit_entry, get_db
from app.models.base import Base
from app.models.calendar_connection import CalendarConnection
from app.calendar.demo_provider import DemoCalendarProvider
from app.oauth.base import OAuthError, OAuthInvalidGrantError
from app.oauth.token_manager import TokenManager
from app.settings import (
    get_oauth_redirect_uri,
    is_google_oauth_configured,
    is_microsoft_oauth_configured,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

# Valid OAuth providers
OAUTH_PROVIDERS = {"google", "microsoft"}
# All valid providers including demo/local
ALL_PROVIDERS = {"demo", "local", "google", "microsoft"}


class OAuthState(Base):
    """Persistent storage for OAuth CSRF state tokens.

    Stores state tokens in the database for production-safe operation
    across server restarts and multi-process deployments.
    """
    __tablename__ = "oauth_state"

    state = Column(String, primary_key=True)
    provider = Column(String, nullable=False)
    redirect_uri = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)


class CalendarConnectionRequest(BaseModel):
    provider: str = Field(min_length=1)
    scopes: list[str]
    token: str = Field(min_length=1)
    enabled: bool = True


class CalendarConnectionResponse(BaseModel):
    connected: bool
    id: str | None = None  # Story 37.5
    name: str | None = None  # Story 37.5
    provider: str | None = None
    scopes: list[str] = []
    enabled: bool = False
    updated_at: datetime | None = None
    # OAuth-specific fields
    token_expires_at: datetime | None = None
    needs_reauth: bool = False
    provider_user_id: str | None = None
    # Sync tracking (Story 37.2)
    last_sync_at: datetime | None = None
    sync_error: str | None = None


class ConnectionUpdateRequest(BaseModel):
    """Request to update a calendar connection (Story 37.5)."""
    name: str | None = None
    enabled: bool | None = None


class OAuthAuthorizeRequest(BaseModel):
    provider: str = Field(min_length=1)


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class OAuthStatusResponse(BaseModel):
    google_configured: bool
    microsoft_configured: bool


class DisconnectResponse(BaseModel):
    status: str
    provider: str


class CalendarPreviewItem(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime
    attendee_count: int


@router.get("/oauth/status", response_model=OAuthStatusResponse)
def get_oauth_status() -> OAuthStatusResponse:
    """Check which OAuth providers are configured."""
    return OAuthStatusResponse(
        google_configured=is_google_oauth_configured(),
        microsoft_configured=is_microsoft_oauth_configured(),
    )


@router.get("/oauth/authorize", response_model=OAuthAuthorizeResponse)
def oauth_authorize(
    provider: str = Query(..., description="OAuth provider: google or microsoft"),
    db: Session = Depends(get_db),
) -> OAuthAuthorizeResponse:
    """Start OAuth authorization flow for a calendar provider.

    Returns the authorization URL to redirect the user to.
    """
    provider = provider.strip().lower()

    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"provider must be one of: {', '.join(OAUTH_PROVIDERS)}",
        )

    # Check if provider is configured
    if provider == "google" and not is_google_oauth_configured():
        raise HTTPException(
            status_code=400,
            detail="Google OAuth is not configured. Set CUSTOS_GOOGLE_CLIENT_ID and CUSTOS_GOOGLE_CLIENT_SECRET.",
        )
    if provider == "microsoft" and not is_microsoft_oauth_configured():
        raise HTTPException(
            status_code=400,
            detail="Microsoft OAuth is not configured. Set CUSTOS_MICROSOFT_CLIENT_ID and CUSTOS_MICROSOFT_CLIENT_SECRET.",
        )

    # Generate CSRF state token
    state = secrets.token_urlsafe(32)
    redirect_uri = get_oauth_redirect_uri()

    # Get authorization URL from provider
    token_manager = TokenManager(db)
    oauth_provider = token_manager.get_provider(provider)
    auth_url = oauth_provider.get_authorization_url(redirect_uri, state)

    # Store state in database for production-safe operation
    now = datetime.now(UTC).replace(tzinfo=None)
    oauth_state = OAuthState(
        state=state,
        provider=provider,
        redirect_uri=redirect_uri,
        created_at=now,
    )
    db.add(oauth_state)

    # Clean up expired states (older than 10 minutes)
    cutoff = now - timedelta(minutes=10)
    db.query(OAuthState).filter(OAuthState.created_at < cutoff).delete()

    add_audit_entry(
        db,
        action="oauth_authorize_started",
        entity_type="CalendarConnection",
        entity_id=f"pending_{state[:16]}",
        payload={"provider": provider},
    )
    db.commit()

    return OAuthAuthorizeResponse(authorization_url=auth_url, state=state)


# Keep POST endpoint for backwards compatibility with existing frontend
@router.post("/oauth/authorize", response_model=OAuthAuthorizeResponse, include_in_schema=False)
def oauth_authorize_post(
    payload: OAuthAuthorizeRequest,
    db: Session = Depends(get_db),
) -> OAuthAuthorizeResponse:
    """POST variant for backwards compatibility."""
    return oauth_authorize(provider=payload.provider, db=db)


@router.post("/oauth/callback", response_model=CalendarConnectionResponse)
def oauth_callback(
    payload: OAuthCallbackRequest,
    db: Session = Depends(get_db),
) -> CalendarConnectionResponse:
    """Handle OAuth callback and exchange code for tokens.

    Stores tokens securely and creates calendar connection.
    """
    code = payload.code.strip()
    state = payload.state.strip()

    # Validate state from database
    oauth_state = db.query(OAuthState).filter(OAuthState.state == state).first()
    if not oauth_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state. Please restart the authorization.",
        )

    # Check if state is expired (10 minute limit)
    now = datetime.now(UTC).replace(tzinfo=None)
    if (now - oauth_state.created_at) > timedelta(minutes=10):
        db.delete(oauth_state)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="OAuth state has expired. Please restart the authorization.",
        )

    provider = oauth_state.provider
    redirect_uri = oauth_state.redirect_uri

    # Delete the used state
    db.delete(oauth_state)

    # Exchange code for tokens
    token_manager = TokenManager(db)
    oauth_provider = token_manager.get_provider(provider)

    try:
        token_response = oauth_provider.exchange_code(code, redirect_uri)
    except OAuthInvalidGrantError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Authorization failed: {e}. Please try again.",
        )
    except OAuthError as e:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth error: {e}",
        )

    # Get user info to store provider_user_id
    provider_user_id = None
    user_info = oauth_provider.get_user_info(token_response.access_token)
    if user_info:
        provider_user_id = user_info.user_id

    # Check if connection already exists
    existing = db.query(CalendarConnection).first()
    if existing:
        connection_id = existing.id
    else:
        connection_id = f"cal_{uuid4().hex}"

    # Store tokens
    connection = token_manager.store_tokens(
        connection_id=connection_id,
        provider=provider,
        token_response=token_response,
        provider_user_id=provider_user_id,
    )
    db.commit()
    db.refresh(connection)

    mark_attempt(enabled=True)

    try:
        scopes = json.loads(connection.scopes) if connection.scopes else []
    except json.JSONDecodeError:
        scopes = []

    return CalendarConnectionResponse(
        connected=True,
        provider=connection.provider,
        scopes=scopes,
        enabled=connection.enabled,
        updated_at=connection.updated_at,
        token_expires_at=connection.token_expires_at,
        needs_reauth=False,
        provider_user_id=connection.provider_user_id,
        last_sync_at=connection.last_sync_at,
        sync_error=connection.sync_error,
    )


@router.delete("/connection", response_model=DisconnectResponse)
def delete_connection(db: Session = Depends(get_db)) -> DisconnectResponse:
    """Disconnect calendar and revoke OAuth tokens if applicable."""
    connection = db.query(CalendarConnection).first()
    if not connection:
        raise HTTPException(status_code=404, detail="No calendar connection exists")

    connection_id = connection.id
    provider = connection.provider

    # For OAuth providers, revoke tokens
    if provider in OAUTH_PROVIDERS:
        token_manager = TokenManager(db)
        try:
            token_manager.revoke_and_delete(connection)
        except Exception as e:
            logger.warning(f"Token revocation failed for {provider}: {e}")
            # Even if revocation fails, delete local connection
            db.delete(connection)
    else:
        # For demo/local, just delete
        add_audit_entry(
            db,
            action="connection_deleted",
            entity_type="CalendarConnection",
            entity_id=connection_id,
            payload={"provider": provider},
        )
        db.delete(connection)

    db.commit()
    mark_attempt(enabled=False)

    return DisconnectResponse(status="disconnected", provider=provider)


@router.post("/connection", response_model=CalendarConnectionResponse)
def set_connection(payload: CalendarConnectionRequest, db: Session = Depends(get_db)) -> CalendarConnectionResponse:
    """Set calendar connection (for demo/local providers only).

    For OAuth providers (google, microsoft), use /oauth/authorize instead.
    """
    provider = payload.provider.strip()
    token = payload.token.strip()
    scopes = [scope.strip() for scope in payload.scopes if scope.strip()]

    # Only allow demo/local through this endpoint
    if provider not in {"demo", "local"}:
        raise HTTPException(
            status_code=422,
            detail="For OAuth providers (google, microsoft), use /oauth/authorize endpoint",
        )
    if not token:
        raise HTTPException(status_code=422, detail="token must not be blank")
    if not scopes:
        raise HTTPException(status_code=422, detail="scopes must not be empty")

    scopes_json = json.dumps(scopes)
    existing = db.query(CalendarConnection).first()
    if existing:
        existing.provider = provider
        existing.scopes = scopes_json
        existing.token = token
        existing.enabled = payload.enabled
        db.add(existing)
        connection = existing
    else:
        connection = CalendarConnection(
            id=f"cal_{uuid4().hex}",
            provider=provider,
            scopes=scopes_json,
            token=token,
            enabled=payload.enabled,
        )
        db.add(connection)
    db.commit()
    db.refresh(connection)
    mark_attempt(enabled=payload.enabled)
    return CalendarConnectionResponse(
        connected=True,
        provider=connection.provider,
        scopes=scopes,
        enabled=connection.enabled,
        updated_at=connection.updated_at,
    )


@router.get("/connection", response_model=CalendarConnectionResponse)
def get_connection(db: Session = Depends(get_db)) -> CalendarConnectionResponse:
    """Get the primary (first) calendar connection for backwards compatibility."""
    connection = db.query(CalendarConnection).first()
    if not connection:
        return CalendarConnectionResponse(connected=False)
    try:
        scopes = json.loads(connection.scopes)
    except json.JSONDecodeError:
        scopes = []

    # Check if OAuth connection needs re-authorization
    needs_reauth = False
    if connection.provider in OAUTH_PROVIDERS:
        # No refresh token means we can't refresh
        if not connection.refresh_token:
            needs_reauth = True
        # Check if token is expired and we can't refresh
        elif connection.is_token_expired() and not connection.enabled:
            needs_reauth = True

    return CalendarConnectionResponse(
        connected=True,
        id=connection.id,  # Story 37.5
        name=connection.name,  # Story 37.5
        provider=connection.provider,
        scopes=scopes,
        enabled=connection.enabled,
        updated_at=connection.updated_at,
        token_expires_at=connection.token_expires_at,
        needs_reauth=needs_reauth,
        provider_user_id=connection.provider_user_id,
        last_sync_at=connection.last_sync_at,
        sync_error=connection.sync_error,
    )


def _get_calendar_provider(connection: CalendarConnection, db: Session):
    """Get the appropriate calendar provider for a connection.

    Handles token refresh for OAuth providers automatically.
    """
    provider_name = connection.provider

    if provider_name == "demo":
        return DemoCalendarProvider()
    elif provider_name == "google":
        from app.calendar.google_provider import GoogleCalendarProvider

        # Refresh token if needed
        token_manager = TokenManager(db)
        try:
            token_manager.refresh_if_needed(connection)
            db.commit()
        except OAuthInvalidGrantError:
            db.commit()
            raise HTTPException(
                status_code=401,
                detail="Google authorization expired. Please reconnect your calendar.",
            )
        return GoogleCalendarProvider(connection.token)
    elif provider_name == "microsoft":
        from app.calendar.microsoft_provider import MicrosoftCalendarProvider

        # Refresh token if needed
        token_manager = TokenManager(db)
        try:
            token_manager.refresh_if_needed(connection)
            db.commit()
        except OAuthInvalidGrantError:
            db.commit()
            raise HTTPException(
                status_code=401,
                detail="Microsoft authorization expired. Please reconnect your calendar.",
            )
        return MicrosoftCalendarProvider(connection.token)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown calendar provider: {provider_name}")


@router.get("/preview")
def preview_calendar(
    range: str = Query("upcoming"),
    db: Session = Depends(get_db),
) -> dict:
    connection = db.query(CalendarConnection).first()
    if not connection:
        raise HTTPException(status_code=400, detail="calendar connection not configured")
    if not connection.enabled:
        raise HTTPException(status_code=400, detail="calendar connection disabled")

    calendar_provider = _get_calendar_provider(connection, db)

    now = datetime.now(UTC).replace(tzinfo=None)
    if range == "today":
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)
    elif range == "upcoming":
        start = now
        end = now + timedelta(days=7)
    else:
        raise HTTPException(status_code=422, detail="range must be today or upcoming")

    events = calendar_provider.list_events(start, end)
    preview = []
    for event in events:
        attendees = calendar_provider.list_attendees(event.event_id)
        preview.append(
            CalendarPreviewItem(
                title=event.title,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                attendee_count=len(attendees),
            ).model_dump()
        )

    return {"range": range, "events": preview, "updated_at": now.isoformat()}


@router.post("/ingest")
def ingest_calendar_now(db: Session = Depends(get_db)) -> dict:
    connection = db.query(CalendarConnection).first()
    if not connection:
        raise HTTPException(status_code=400, detail="calendar connection not configured")
    if not connection.enabled:
        raise HTTPException(status_code=400, detail="calendar connection disabled")

    provider = _get_calendar_provider(connection, db)
    result = ingest_calendar(provider, db)
    return {"status": result.get("status"), "events": result.get("events", 0)}


@router.get("/connections")
def list_connections(db: Session = Depends(get_db)) -> dict:
    """
    List all calendar connections.

    Story 37.5: Multi-Calendar Support
    """
    connections = db.query(CalendarConnection).order_by(CalendarConnection.created_at).all()

    result = []
    for conn in connections:
        try:
            scopes = json.loads(conn.scopes) if conn.scopes else []
        except json.JSONDecodeError:
            scopes = []

        needs_reauth = False
        if conn.provider in OAUTH_PROVIDERS:
            if not conn.refresh_token:
                needs_reauth = True
            elif conn.is_token_expired() and not conn.enabled:
                needs_reauth = True

        result.append({
            "id": conn.id,
            "name": conn.name,
            "provider": conn.provider,
            "scopes": scopes,
            "enabled": conn.enabled,
            "updated_at": conn.updated_at.isoformat() if conn.updated_at else None,
            "token_expires_at": conn.token_expires_at.isoformat() if conn.token_expires_at else None,
            "needs_reauth": needs_reauth,
            "provider_user_id": conn.provider_user_id,
            "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
            "sync_error": conn.sync_error,
        })

    return {
        "count": len(result),
        "connections": result,
    }


@router.patch("/connections/{connection_id}")
def update_connection(
    connection_id: str,
    payload: ConnectionUpdateRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Update a calendar connection's name or enabled status.

    Story 37.5: Multi-Calendar Support
    """
    connection = db.get(CalendarConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    if payload.name is not None:
        connection.name = payload.name.strip() if payload.name else None

    if payload.enabled is not None:
        connection.enabled = payload.enabled

    add_audit_entry(
        db,
        action="connection_updated",
        entity_type="CalendarConnection",
        entity_id=connection_id,
        payload={"name": connection.name, "enabled": connection.enabled},
    )

    db.commit()
    db.refresh(connection)

    try:
        scopes = json.loads(connection.scopes) if connection.scopes else []
    except json.JSONDecodeError:
        scopes = []

    return {
        "id": connection.id,
        "name": connection.name,
        "provider": connection.provider,
        "scopes": scopes,
        "enabled": connection.enabled,
        "updated_at": connection.updated_at.isoformat() if connection.updated_at else None,
        "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
        "sync_error": connection.sync_error,
    }


@router.delete("/connections/{connection_id}")
def delete_specific_connection(
    connection_id: str,
    db: Session = Depends(get_db),
) -> DisconnectResponse:
    """
    Delete a specific calendar connection.

    Story 37.5: Multi-Calendar Support
    """
    connection = db.get(CalendarConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    provider = connection.provider

    # For OAuth providers, revoke tokens
    if provider in OAUTH_PROVIDERS:
        token_manager = TokenManager(db)
        try:
            token_manager.revoke_and_delete(connection)
        except Exception as e:
            logger.warning(f"Token revocation failed for {provider}: {e}")
            db.delete(connection)
    else:
        add_audit_entry(
            db,
            action="connection_deleted",
            entity_type="CalendarConnection",
            entity_id=connection_id,
            payload={"provider": provider, "name": connection.name},
        )
        db.delete(connection)

    db.commit()

    return DisconnectResponse(status="disconnected", provider=provider)


@router.get("/conflicts")
def get_calendar_conflicts(db: Session = Depends(get_db)) -> dict:
    """
    Get meetings with sync conflicts (local overrides that differ from calendar).

    Story 37.4: Sync Conflict Resolution
    """
    from app.models.meeting import Meeting

    # Find all calendar meetings with local overrides
    overridden = (
        db.query(Meeting)
        .filter(
            Meeting.source == "calendar",
            Meeting.local_override.is_(True),
            Meeting.cancelled_at.is_(None),
        )
        .order_by(Meeting.starts_at.asc())
        .all()
    )

    conflicts = []
    for meeting in overridden:
        conflict_details = meeting.get_conflicts()
        if conflict_details:
            conflicts.append({
                "meeting_id": meeting.id,
                "meeting_title": meeting.title,
                "starts_at": meeting.starts_at.isoformat() if meeting.starts_at else None,
                "conflicts": conflict_details,
            })

    return {
        "count": len(conflicts),
        "conflicts": conflicts,
        "updated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
    }
