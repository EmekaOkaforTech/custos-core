"""OAuth provider base protocol and common types.

Epic 37: Live Calendar Sync - Story 37.1
Defines the interface all OAuth providers must implement.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Protocol


@dataclass
class TokenResponse:
    """Response from OAuth token exchange or refresh."""

    access_token: str
    token_type: str
    expires_in: int  # Seconds until expiration
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None  # For providers that return identity info

    def get_expiry_datetime(self) -> datetime:
        """Calculate the expiration datetime from expires_in."""
        return datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=self.expires_in)


@dataclass
class UserInfo:
    """Basic user information from OAuth provider."""

    user_id: str
    email: str | None = None
    name: str | None = None


class OAuthProvider(Protocol):
    """Protocol defining OAuth provider interface.

    All OAuth providers (Google, Microsoft) must implement this protocol.
    """

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Generate the OAuth authorization URL for user consent.

        Args:
            redirect_uri: URL to redirect after authorization
            state: CSRF protection state parameter

        Returns:
            Full authorization URL to redirect user to
        """
        ...

    def exchange_code(self, code: str, redirect_uri: str) -> TokenResponse:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Must match the original redirect_uri

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            OAuthError: If code exchange fails
        """
        ...

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh an expired access token.

        Args:
            refresh_token: The refresh token from initial authorization

        Returns:
            TokenResponse with new access token (and possibly new refresh token)

        Raises:
            OAuthError: If refresh fails (e.g., refresh token revoked)
        """
        ...

    def revoke_token(self, token: str) -> bool:
        """Revoke a token (access or refresh).

        Args:
            token: The token to revoke

        Returns:
            True if revocation succeeded, False otherwise
        """
        ...

    def get_user_info(self, access_token: str) -> UserInfo | None:
        """Get basic user information using the access token.

        Args:
            access_token: Valid access token

        Returns:
            UserInfo if available, None if not supported or fails
        """
        ...


class OAuthError(Exception):
    """Base exception for OAuth errors."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class OAuthTokenExpiredError(OAuthError):
    """Token has expired and cannot be refreshed."""

    pass


class OAuthInvalidGrantError(OAuthError):
    """Authorization code or refresh token is invalid."""

    pass
