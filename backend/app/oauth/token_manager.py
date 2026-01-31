"""Token manager for OAuth token lifecycle management.

Epic 37: Live Calendar Sync - Story 37.1
Handles automatic token refresh and secure token operations.
"""

from datetime import datetime, UTC
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.db import add_audit_entry
from app.models.calendar_connection import CalendarConnection

from .base import OAuthError, OAuthInvalidGrantError, TokenResponse
from .google import GoogleOAuthProvider
from .microsoft import MicrosoftOAuthProvider

if TYPE_CHECKING:
    from .base import OAuthProvider


class TokenManager:
    """Manages OAuth token lifecycle for calendar connections.

    Handles:
    - Automatic token refresh before expiration
    - Secure token storage (via SQLCipher)
    - Token revocation
    - Audit logging of all token operations
    """

    def __init__(self, db: Session):
        """Initialize token manager.

        Args:
            db: SQLAlchemy session for database operations
        """
        self.db = db

    def get_provider(self, provider_name: str) -> "OAuthProvider":
        """Get the OAuth provider instance by name.

        Args:
            provider_name: "google" or "microsoft"

        Returns:
            OAuth provider instance

        Raises:
            OAuthError: If provider name is invalid
        """
        if provider_name == "google":
            return GoogleOAuthProvider()
        elif provider_name == "microsoft":
            return MicrosoftOAuthProvider()
        else:
            raise OAuthError(f"Unknown OAuth provider: {provider_name}", error_code="invalid_provider")

    def store_tokens(
        self,
        connection_id: str,
        provider: str,
        token_response: TokenResponse,
        provider_user_id: str | None = None,
    ) -> CalendarConnection:
        """Store OAuth tokens in the database.

        Args:
            connection_id: Unique ID for the connection
            provider: Provider name ("google" or "microsoft")
            token_response: Token response from OAuth flow
            provider_user_id: User ID from provider (optional)

        Returns:
            CalendarConnection record
        """
        now = datetime.now(UTC).replace(tzinfo=None)

        # Check if connection exists
        connection = self.db.get(CalendarConnection, connection_id)

        if connection:
            # Update existing connection
            connection.token = token_response.access_token
            connection.refresh_token = token_response.refresh_token or connection.refresh_token
            connection.token_expires_at = token_response.get_expiry_datetime()
            connection.last_refresh_at = now
            connection.updated_at = now
            if provider_user_id:
                connection.provider_user_id = provider_user_id
        else:
            # Create new connection
            import json
            scopes = token_response.scope.split() if token_response.scope else []
            connection = CalendarConnection(
                id=connection_id,
                provider=provider,
                scopes=json.dumps(scopes),
                token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                token_expires_at=token_response.get_expiry_datetime(),
                last_refresh_at=now,
                provider_user_id=provider_user_id,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
            self.db.add(connection)

        # Audit log (never log actual tokens)
        add_audit_entry(
            self.db,
            action="token_stored",
            entity_type="CalendarConnection",
            entity_id=connection_id,
            payload={
                "provider": provider,
                "has_refresh_token": bool(token_response.refresh_token),
                "expires_in": token_response.expires_in,
            },
        )

        return connection

    def refresh_if_needed(self, connection: CalendarConnection) -> bool:
        """Refresh token if expired or about to expire.

        Args:
            connection: Calendar connection to check/refresh

        Returns:
            True if refresh was performed, False if not needed

        Raises:
            OAuthError: If no refresh token is available
            OAuthInvalidGrantError: If refresh token is invalid
        """
        # Check if token is expired (needs refresh check includes refresh_token presence)
        if not connection.is_token_expired():
            return False

        if not connection.refresh_token:
            raise OAuthError(
                "Cannot refresh: no refresh token available",
                error_code="no_refresh_token",
            )

        provider = self.get_provider(connection.provider)
        try:
            token_response = provider.refresh_token(connection.refresh_token)
        except OAuthInvalidGrantError:
            # Mark connection as needing re-authorization
            connection.enabled = False
            connection.updated_at = datetime.now(UTC).replace(tzinfo=None)

            add_audit_entry(
                self.db,
                action="token_refresh_failed",
                entity_type="CalendarConnection",
                entity_id=connection.id,
                payload={"provider": connection.provider, "reason": "invalid_grant"},
            )
            raise

        # Update tokens
        now = datetime.now(UTC).replace(tzinfo=None)
        connection.token = token_response.access_token
        if token_response.refresh_token:
            connection.refresh_token = token_response.refresh_token
        connection.token_expires_at = token_response.get_expiry_datetime()
        connection.last_refresh_at = now
        connection.updated_at = now

        add_audit_entry(
            self.db,
            action="token_refreshed",
            entity_type="CalendarConnection",
            entity_id=connection.id,
            payload={
                "provider": connection.provider,
                "new_expires_in": token_response.expires_in,
            },
        )

        return True

    def revoke_and_delete(self, connection: CalendarConnection) -> bool:
        """Revoke tokens and delete the connection.

        Args:
            connection: Calendar connection to revoke and delete

        Returns:
            True if successful
        """
        provider = self.get_provider(connection.provider)
        connection_id = connection.id
        connection_provider = connection.provider

        # Try to revoke refresh token first (more important)
        if connection.refresh_token:
            provider.revoke_token(connection.refresh_token)

        # Revoke access token
        if connection.token:
            provider.revoke_token(connection.token)

        # Delete connection from database
        self.db.delete(connection)

        add_audit_entry(
            self.db,
            action="token_revoked",
            entity_type="CalendarConnection",
            entity_id=connection_id,
            payload={"provider": connection_provider},
        )

        return True

    def get_valid_token(self, connection: CalendarConnection) -> str:
        """Get a valid access token, refreshing if necessary.

        Args:
            connection: Calendar connection

        Returns:
            Valid access token

        Raises:
            OAuthError: If token cannot be obtained
        """
        self.refresh_if_needed(connection)
        return connection.token
