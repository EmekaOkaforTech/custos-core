"""Microsoft OAuth provider for Outlook/Graph Calendar integration.

Epic 37: Live Calendar Sync - Story 37.1
Implements OAuth2 flow for Microsoft 365/Outlook Calendar using Microsoft Graph API.
"""

import logging
from urllib.parse import urlencode

import httpx

from app.settings import get_microsoft_client_id, get_microsoft_client_secret

from .base import (
    OAuthError,
    OAuthInvalidGrantError,
    OAuthProvider,
    TokenResponse,
    UserInfo,
)

logger = logging.getLogger(__name__)

# Microsoft OAuth endpoints (using 'common' for personal and work accounts)
MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

# Default scopes for calendar read access and user info
MICROSOFT_CALENDAR_SCOPES = [
    "Calendars.Read",
    "User.Read",
    "offline_access",  # Required for refresh token
]


class MicrosoftOAuthProvider:
    """Microsoft OAuth2 provider for Outlook/Graph Calendar integration.

    Implements the OAuthProvider protocol for Microsoft Calendar access.
    Supports both personal Microsoft accounts and work/school accounts.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
    ):
        """Initialize Microsoft OAuth provider.

        Args:
            client_id: Microsoft OAuth client ID (defaults to env var)
            client_secret: Microsoft OAuth client secret (defaults to env var)
            scopes: OAuth scopes to request (defaults to Calendars.Read)
        """
        self.client_id = client_id or get_microsoft_client_id()
        self.client_secret = client_secret or get_microsoft_client_secret()
        self.scopes = scopes or MICROSOFT_CALENDAR_SCOPES

        if not self.client_id or not self.client_secret:
            raise OAuthError(
                "Microsoft OAuth credentials not configured. "
                "Set CUSTOS_MICROSOFT_CLIENT_ID and CUSTOS_MICROSOFT_CLIENT_SECRET.",
                error_code="credentials_missing",
            )

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Generate Microsoft OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authorization
            state: CSRF protection state parameter

        Returns:
            Full authorization URL for Microsoft OAuth consent screen
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "response_mode": "query",
            "prompt": "consent",  # Always show consent to get refresh token
        }
        return f"{MICROSOFT_AUTH_URL}?{urlencode(params)}"

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
            "scope": " ".join(self.scopes),
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                MICROSOFT_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

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
            "scope": " ".join(self.scopes),
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                MICROSOFT_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

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
            refresh_token=token_data.get("refresh_token", refresh_token),
            scope=token_data.get("scope"),
        )

    def revoke_token(self, token: str) -> bool:
        """Revoke a token.

        Note: Microsoft Graph doesn't have a standard revoke endpoint.
        The recommended approach is to delete the refresh token from storage.
        This method always returns True as we handle revocation by deletion.

        Args:
            token: The token to revoke (not used for Microsoft)

        Returns:
            Always True (revocation handled by token deletion)
        """
        # Microsoft doesn't have a public revoke endpoint
        # Revocation is handled by deleting tokens from our storage
        return True

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
                response = client.get(MICROSOFT_USERINFO_URL, headers=headers)

            if response.status_code != 200:
                logger.warning(
                    "Microsoft user info request failed with status %d",
                    response.status_code,
                )
                return None

            data = response.json()
            return UserInfo(
                user_id=data.get("id", ""),
                email=data.get("mail") or data.get("userPrincipalName"),
                name=data.get("displayName"),
            )
        except Exception as e:
            logger.warning("Failed to get Microsoft user info: %s", str(e))
            return None


# Verify protocol compliance
def _check_protocol() -> None:
    """Type check that MicrosoftOAuthProvider implements OAuthProvider."""
    provider: OAuthProvider = MicrosoftOAuthProvider.__new__(MicrosoftOAuthProvider)
    _ = provider
