"""Google OAuth provider for Google Calendar integration.

Epic 37: Live Calendar Sync - Story 37.1
Implements OAuth2 flow for Google Calendar using Google's OAuth endpoints.
"""

import logging
from urllib.parse import urlencode

import httpx

from app.settings import get_google_client_id, get_google_client_secret

from .base import (
    OAuthError,
    OAuthInvalidGrantError,
    OAuthProvider,
    TokenResponse,
    UserInfo,
)

logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Default scopes for calendar read access
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
]


class GoogleOAuthProvider:
    """Google OAuth2 provider for Calendar integration.

    Implements the OAuthProvider protocol for Google Calendar access.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
    ):
        """Initialize Google OAuth provider.

        Args:
            client_id: Google OAuth client ID (defaults to env var)
            client_secret: Google OAuth client secret (defaults to env var)
            scopes: OAuth scopes to request (defaults to calendar.readonly)
        """
        self.client_id = client_id or get_google_client_id()
        self.client_secret = client_secret or get_google_client_secret()
        self.scopes = scopes or GOOGLE_CALENDAR_SCOPES

        if not self.client_id or not self.client_secret:
            raise OAuthError(
                "Google OAuth credentials not configured. "
                "Set CUSTOS_GOOGLE_CLIENT_ID and CUSTOS_GOOGLE_CLIENT_SECRET.",
                error_code="credentials_missing",
            )

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Generate Google OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authorization
            state: CSRF protection state parameter

        Returns:
            Full authorization URL for Google OAuth consent screen
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Always show consent to get refresh token
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

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
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error = error_data.get("error", "unknown_error")
            error_desc = error_data.get("error_description", "Token exchange failed")

            if error == "invalid_grant":
                raise OAuthInvalidGrantError(error_desc, error_code=error)
            raise OAuthError(error_desc, error_code=error)

        token_data = response.json()
        return TokenResponse(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
            id_token=token_data.get("id_token"),
        )

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh an expired access token.

        Args:
            refresh_token: The refresh token from initial authorization

        Returns:
            TokenResponse with new access token

        Raises:
            OAuthError: If refresh fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error = error_data.get("error", "unknown_error")
            error_desc = error_data.get("error_description", "Token refresh failed")

            if error == "invalid_grant":
                raise OAuthInvalidGrantError(
                    "Refresh token is invalid or revoked. User must re-authorize.",
                    error_code=error,
                )
            raise OAuthError(error_desc, error_code=error)

        token_data = response.json()
        return TokenResponse(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token", refresh_token),  # May return new refresh token
            scope=token_data.get("scope"),
        )

    def revoke_token(self, token: str) -> bool:
        """Revoke a token (access or refresh).

        Args:
            token: The token to revoke

        Returns:
            True if revocation succeeded, False otherwise
        """
        with httpx.Client(timeout=30.0) as client:
            response = client.post(GOOGLE_REVOKE_URL, params={"token": token})

        # Google returns 200 on success, 400 if token already revoked
        return response.status_code in (200, 400)

    def get_user_info(self, access_token: str) -> UserInfo | None:
        """Get basic user information using the access token.

        Args:
            access_token: Valid access token

        Returns:
            UserInfo with user's email and ID, or None if fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(GOOGLE_USERINFO_URL, headers=headers)

            if response.status_code != 200:
                logger.warning(
                    "Google user info request failed with status %d",
                    response.status_code,
                )
                return None

            data = response.json()
            return UserInfo(
                user_id=data.get("id", ""),
                email=data.get("email"),
                name=data.get("name"),
            )
        except Exception as e:
            logger.warning("Failed to get Google user info: %s", str(e))
            return None


# Verify protocol compliance
def _check_protocol() -> None:
    """Type check that GoogleOAuthProvider implements OAuthProvider."""
    provider: OAuthProvider = GoogleOAuthProvider.__new__(GoogleOAuthProvider)
    _ = provider
