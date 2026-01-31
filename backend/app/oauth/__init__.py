"""OAuth provider modules for calendar integration.

Epic 37: Live Calendar Sync - Story 37.1
Provides OAuth2 authentication for Google Calendar and Microsoft Outlook.
"""

from .base import OAuthProvider, TokenResponse
from .google import GoogleOAuthProvider
from .microsoft import MicrosoftOAuthProvider
from .token_manager import TokenManager

__all__ = [
    "OAuthProvider",
    "TokenResponse",
    "GoogleOAuthProvider",
    "MicrosoftOAuthProvider",
    "TokenManager",
]
