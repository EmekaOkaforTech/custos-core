"""Tests for OAuth calendar integration - Epic 37 Story 37.1."""

import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Ensure test environment
os.environ.setdefault("CUSTOS_ALLOW_PLAINTEXT_DB", "1")
os.environ.setdefault("CUSTOS_DATABASE_KEY", "test-key")

from fastapi.testclient import TestClient

from app.main import app
from app.models.calendar_connection import CalendarConnection
from app.oauth.base import OAuthError, OAuthInvalidGrantError, TokenResponse
from app.oauth.token_manager import TokenManager


@pytest.fixture
def client(test_app):
    """Test client with fresh database."""
    return TestClient(test_app)


class TestOAuthStatus:
    """Tests for /api/calendar/oauth/status endpoint."""

    def test_oauth_status_unconfigured(self, client):
        """Returns false when OAuth is not configured."""
        with patch("app.api.calendar.is_google_oauth_configured", return_value=False):
            with patch("app.api.calendar.is_microsoft_oauth_configured", return_value=False):
                response = client.get("/api/calendar/oauth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["google_configured"] is False
        assert data["microsoft_configured"] is False

    def test_oauth_status_google_configured(self, client):
        """Returns true when Google OAuth is configured."""
        with patch("app.api.calendar.is_google_oauth_configured", return_value=True):
            with patch("app.api.calendar.is_microsoft_oauth_configured", return_value=False):
                response = client.get("/api/calendar/oauth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["google_configured"] is True
        assert data["microsoft_configured"] is False

    def test_oauth_status_both_configured(self, client):
        """Returns true when both providers are configured."""
        with patch("app.api.calendar.is_google_oauth_configured", return_value=True):
            with patch("app.api.calendar.is_microsoft_oauth_configured", return_value=True):
                response = client.get("/api/calendar/oauth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["google_configured"] is True
        assert data["microsoft_configured"] is True


class TestOAuthAuthorize:
    """Tests for /api/calendar/oauth/authorize endpoint."""

    def test_authorize_invalid_provider(self, client):
        """Rejects invalid provider names."""
        response = client.get("/api/calendar/oauth/authorize?provider=invalid")
        assert response.status_code == 422
        assert "must be one of" in response.json()["detail"]

    def test_authorize_demo_not_oauth(self, client):
        """Demo provider cannot use OAuth flow."""
        response = client.get("/api/calendar/oauth/authorize?provider=demo")
        assert response.status_code == 422

    def test_authorize_google_not_configured(self, client):
        """Fails when Google OAuth is not configured."""
        with patch("app.api.calendar.is_google_oauth_configured", return_value=False):
            response = client.get("/api/calendar/oauth/authorize?provider=google")

        assert response.status_code == 400
        assert "not configured" in response.json()["detail"]

    def test_authorize_google_success(self, client):
        """Returns authorization URL for Google."""
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = "https://accounts.google.com/oauth/authorize?..."

        with patch("app.api.calendar.is_google_oauth_configured", return_value=True):
            with patch("app.oauth.token_manager.GoogleOAuthProvider", return_value=mock_provider):
                response = client.get("/api/calendar/oauth/authorize?provider=google")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert len(data["state"]) > 20  # Should be a secure random string

    def test_authorize_microsoft_not_configured(self, client):
        """Fails when Microsoft OAuth is not configured."""
        with patch("app.api.calendar.is_microsoft_oauth_configured", return_value=False):
            response = client.get("/api/calendar/oauth/authorize?provider=microsoft")

        assert response.status_code == 400
        assert "not configured" in response.json()["detail"]

    def test_authorize_post_backwards_compat(self, client):
        """POST endpoint works for backwards compatibility."""
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = "https://accounts.google.com/oauth/authorize?..."

        with patch("app.api.calendar.is_google_oauth_configured", return_value=True):
            with patch("app.oauth.token_manager.GoogleOAuthProvider", return_value=mock_provider):
                response = client.post(
                    "/api/calendar/oauth/authorize",
                    json={"provider": "google"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data


class TestOAuthCallback:
    """Tests for /api/calendar/oauth/callback endpoint."""

    def test_callback_invalid_state(self, client):
        """Rejects invalid state parameter."""
        response = client.post(
            "/api/calendar/oauth/callback",
            json={"code": "test_code", "state": "invalid_state"},
        )
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    def test_callback_success(self, client):
        """Successfully exchanges code for tokens."""
        # First, start authorization to get a valid state
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = "https://accounts.google.com/oauth"

        with patch("app.api.calendar.is_google_oauth_configured", return_value=True):
            with patch("app.oauth.token_manager.GoogleOAuthProvider", return_value=mock_provider):
                auth_response = client.get("/api/calendar/oauth/authorize?provider=google")

        state = auth_response.json()["state"]

        # Now simulate callback
        mock_token_response = TokenResponse(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="calendar.readonly",
        )
        mock_user_info = MagicMock()
        mock_user_info.user_id = "google_user_123"

        mock_provider.exchange_code.return_value = mock_token_response
        mock_provider.get_user_info.return_value = mock_user_info

        with patch("app.oauth.token_manager.GoogleOAuthProvider", return_value=mock_provider):
            response = client.post(
                "/api/calendar/oauth/callback",
                json={"code": "auth_code_123", "state": state},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["provider"] == "google"
        assert data["provider_user_id"] == "google_user_123"

    def test_callback_invalid_grant(self, client):
        """Handles invalid grant error from provider."""
        # Start authorization
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = "https://accounts.google.com/oauth"

        with patch("app.api.calendar.is_google_oauth_configured", return_value=True):
            with patch("app.oauth.token_manager.GoogleOAuthProvider", return_value=mock_provider):
                auth_response = client.get("/api/calendar/oauth/authorize?provider=google")

        state = auth_response.json()["state"]

        # Callback fails with invalid grant
        mock_provider.exchange_code.side_effect = OAuthInvalidGrantError("Code expired")

        with patch("app.oauth.token_manager.GoogleOAuthProvider", return_value=mock_provider):
            response = client.post(
                "/api/calendar/oauth/callback",
                json={"code": "expired_code", "state": state},
            )

        assert response.status_code == 400
        assert "Authorization failed" in response.json()["detail"]


class TestDeleteConnection:
    """Tests for DELETE /api/calendar/connection endpoint."""

    def test_delete_no_connection(self, client):
        """Returns 404 when no connection exists."""
        response = client.delete("/api/calendar/connection")
        assert response.status_code == 404

    def test_delete_demo_connection(self, client, test_db):
        """Deletes demo connection without OAuth revocation."""
        # Create demo connection
        connection = CalendarConnection(
            id="cal_test123",
            provider="demo",
            scopes=json.dumps(["read"]),
            token="demo_token",
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        response = client.delete("/api/calendar/connection")
        assert response.status_code == 200
        assert response.json()["status"] == "disconnected"

        # Verify connection deleted
        test_db.expire_all()
        assert test_db.query(CalendarConnection).first() is None

    def test_delete_oauth_connection(self, client, test_db):
        """Deletes OAuth connection with token revocation."""
        # Create Google OAuth connection
        connection = CalendarConnection(
            id="cal_google123",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="access_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        mock_provider = MagicMock()
        mock_provider.revoke_token.return_value = True

        with patch("app.oauth.token_manager.GoogleOAuthProvider", return_value=mock_provider):
            response = client.delete("/api/calendar/connection")

        assert response.status_code == 200
        assert response.json()["provider"] == "google"

        # Verify revoke was called
        assert mock_provider.revoke_token.call_count == 2  # refresh + access


class TestTokenManager:
    """Unit tests for TokenManager class."""

    def test_get_provider_google(self, test_db):
        """Returns GoogleOAuthProvider for google."""
        with patch("app.oauth.token_manager.GoogleOAuthProvider") as mock_class:
            mock_class.return_value = MagicMock()
            manager = TokenManager(test_db)
            provider = manager.get_provider("google")
            mock_class.assert_called_once()

    def test_get_provider_microsoft(self, test_db):
        """Returns MicrosoftOAuthProvider for microsoft."""
        with patch("app.oauth.token_manager.MicrosoftOAuthProvider") as mock_class:
            mock_class.return_value = MagicMock()
            manager = TokenManager(test_db)
            provider = manager.get_provider("microsoft")
            mock_class.assert_called_once()

    def test_get_provider_invalid(self, test_db):
        """Raises OAuthError for invalid provider."""
        manager = TokenManager(test_db)
        with pytest.raises(OAuthError):
            manager.get_provider("invalid")

    def test_store_tokens_new_connection(self, test_db):
        """Creates new connection when none exists."""
        manager = TokenManager(test_db)
        token_response = TokenResponse(
            access_token="new_access",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="new_refresh",
            scope="calendar.readonly",
        )

        connection = manager.store_tokens(
            connection_id="cal_new123",
            provider="google",
            token_response=token_response,
            provider_user_id="user123",
        )
        test_db.commit()

        assert connection.id == "cal_new123"
        assert connection.provider == "google"
        assert connection.token == "new_access"
        assert connection.refresh_token == "new_refresh"
        assert connection.provider_user_id == "user123"

    def test_store_tokens_update_existing(self, test_db):
        """Updates existing connection."""
        # Create existing connection
        existing = CalendarConnection(
            id="cal_existing",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="old_access",
            refresh_token="old_refresh",
            enabled=True,
        )
        test_db.add(existing)
        test_db.commit()

        manager = TokenManager(test_db)
        token_response = TokenResponse(
            access_token="updated_access",
            token_type="Bearer",
            expires_in=7200,
            refresh_token="updated_refresh",
        )

        connection = manager.store_tokens(
            connection_id="cal_existing",
            provider="google",
            token_response=token_response,
        )
        test_db.commit()

        assert connection.token == "updated_access"
        assert connection.refresh_token == "updated_refresh"

    def test_refresh_if_needed_not_expired(self, test_db):
        """Does not refresh if token is not expired."""
        connection = CalendarConnection(
            id="cal_fresh",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="fresh_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        manager = TokenManager(test_db)
        result = manager.refresh_if_needed(connection)

        assert result is False  # No refresh performed

    def test_refresh_if_needed_expired(self, test_db):
        """Refreshes token when expired."""
        connection = CalendarConnection(
            id="cal_expired",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="expired_token",
            refresh_token="valid_refresh",
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5),
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        mock_provider = MagicMock()
        mock_provider.refresh_token.return_value = TokenResponse(
            access_token="new_access",
            token_type="Bearer",
            expires_in=3600,
        )

        manager = TokenManager(test_db)
        with patch.object(manager, "get_provider", return_value=mock_provider):
            result = manager.refresh_if_needed(connection)

        assert result is True
        assert connection.token == "new_access"

    def test_refresh_if_needed_no_refresh_token(self, test_db):
        """Raises error when no refresh token available."""
        connection = CalendarConnection(
            id="cal_no_refresh",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="access_token",
            refresh_token=None,
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5),
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        manager = TokenManager(test_db)
        with pytest.raises(OAuthError) as exc_info:
            manager.refresh_if_needed(connection)

        assert "no refresh token" in str(exc_info.value)

    def test_refresh_if_needed_invalid_grant(self, test_db):
        """Disables connection on invalid grant error."""
        connection = CalendarConnection(
            id="cal_revoked",
            provider="google",
            scopes=json.dumps(["calendar.readonly"]),
            token="access_token",
            refresh_token="revoked_refresh",
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5),
            enabled=True,
        )
        test_db.add(connection)
        test_db.commit()

        mock_provider = MagicMock()
        mock_provider.refresh_token.side_effect = OAuthInvalidGrantError("Token revoked")

        manager = TokenManager(test_db)
        with patch.object(manager, "get_provider", return_value=mock_provider):
            with pytest.raises(OAuthInvalidGrantError):
                manager.refresh_if_needed(connection)

        assert connection.enabled is False


class TestCalendarConnectionModel:
    """Tests for CalendarConnection model methods."""

    def test_is_token_expired_no_expiry(self):
        """Returns False when no expiry is set."""
        connection = CalendarConnection(
            id="cal_test",
            provider="google",
            scopes="[]",
            token="token",
            token_expires_at=None,
            enabled=True,
        )
        assert connection.is_token_expired() is False

    def test_is_token_expired_future(self):
        """Returns False when token expires in future."""
        connection = CalendarConnection(
            id="cal_test",
            provider="google",
            scopes="[]",
            token="token",
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
            enabled=True,
        )
        assert connection.is_token_expired() is False

    def test_is_token_expired_past(self):
        """Returns True when token is expired."""
        connection = CalendarConnection(
            id="cal_test",
            provider="google",
            scopes="[]",
            token="token",
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5),
            enabled=True,
        )
        assert connection.is_token_expired() is True

    def test_needs_refresh_no_expiry(self):
        """Returns False when no expiry is set."""
        connection = CalendarConnection(
            id="cal_test",
            provider="google",
            scopes="[]",
            token="token",
            token_expires_at=None,
            enabled=True,
        )
        assert connection.needs_refresh() is False

    def test_needs_refresh_soon(self):
        """Returns True when token expires within buffer and has refresh token."""
        connection = CalendarConnection(
            id="cal_test",
            provider="google",
            scopes="[]",
            token="token",
            refresh_token="refresh_token",  # Need refresh token to trigger refresh
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=3),
            enabled=True,
        )
        assert connection.needs_refresh() is True

    def test_needs_refresh_not_soon(self):
        """Returns False when token expires after buffer."""
        connection = CalendarConnection(
            id="cal_test",
            provider="google",
            scopes="[]",
            token="token",
            token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
            enabled=True,
        )
        assert connection.needs_refresh() is False
