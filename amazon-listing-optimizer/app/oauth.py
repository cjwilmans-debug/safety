"""
Amazon Login with Amazon (LWA) OAuth 2.0 Handler.
Handles the OAuth flow for connecting to Amazon SP-API.
"""
import secrets
import httpx
from urllib.parse import urlencode
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from .config import get_settings, AmazonOAuthConfig


class TokenData(BaseModel):
    """OAuth token data model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires_at is None:
            return True
        return datetime.utcnow() >= self.expires_at


class OAuthState(BaseModel):
    """OAuth state for CSRF protection."""
    state: str
    created_at: datetime
    marketplace: str = "US"


# In-memory storage (use Redis/DB in production)
oauth_states: dict[str, OAuthState] = {}
stored_tokens: dict[str, TokenData] = {}


class AmazonOAuth:
    """Amazon LWA OAuth 2.0 handler."""

    def __init__(self):
        self.settings = get_settings()
        self.config = AmazonOAuthConfig()

    def generate_authorization_url(self, marketplace: str = "US") -> tuple[str, str]:
        """
        Generate the Amazon OAuth authorization URL.
        Returns (authorization_url, state).
        """
        # Generate secure random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state for validation
        oauth_states[state] = OAuthState(
            state=state,
            created_at=datetime.utcnow(),
            marketplace=marketplace
        )

        # Build authorization URL parameters
        params = {
            "client_id": self.settings.lwa_client_id,
            "scope": " ".join(self.config.SCOPES),
            "response_type": "code",
            "redirect_uri": self.settings.oauth_redirect_uri,
            "state": state,
        }

        # Add application_id for SP-API
        if self.settings.sp_api_app_id:
            params["application_id"] = self.settings.sp_api_app_id

        authorization_url = f"{self.config.AUTHORIZE_URL}?{urlencode(params)}"

        return authorization_url, state

    def validate_state(self, state: str) -> Optional[OAuthState]:
        """
        Validate OAuth state parameter.
        Returns the OAuthState if valid, None otherwise.
        """
        if state not in oauth_states:
            return None

        oauth_state = oauth_states[state]

        # Check if state is expired (10 minutes max)
        if datetime.utcnow() - oauth_state.created_at > timedelta(minutes=10):
            del oauth_states[state]
            return None

        # Remove used state
        del oauth_states[state]
        return oauth_state

    async def exchange_code_for_tokens(self, code: str) -> TokenData:
        """
        Exchange authorization code for access and refresh tokens.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.settings.oauth_redirect_uri,
                    "client_id": self.settings.lwa_client_id,
                    "client_secret": self.settings.lwa_client_secret,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"Token exchange failed: {error_data}")

            data = response.json()

            token_data = TokenData(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                token_type=data.get("token_type", "bearer"),
                expires_in=data.get("expires_in", 3600),
                expires_at=datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
            )

            # Store tokens (use secure storage in production)
            stored_tokens["default"] = token_data

            return token_data

    async def refresh_access_token(self, refresh_token: str) -> TokenData:
        """
        Refresh an expired access token using the refresh token.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.settings.lwa_client_id,
                    "client_secret": self.settings.lwa_client_secret,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"Token refresh failed: {error_data}")

            data = response.json()

            token_data = TokenData(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", refresh_token),
                token_type=data.get("token_type", "bearer"),
                expires_in=data.get("expires_in", 3600),
                expires_at=datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
            )

            # Update stored tokens
            stored_tokens["default"] = token_data

            return token_data

    async def get_valid_access_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        """
        if "default" not in stored_tokens:
            return None

        token_data = stored_tokens["default"]

        if token_data.is_expired():
            try:
                token_data = await self.refresh_access_token(token_data.refresh_token)
            except Exception:
                return None

        return token_data.access_token

    def get_stored_tokens(self) -> Optional[TokenData]:
        """Get currently stored tokens."""
        return stored_tokens.get("default")

    def clear_tokens(self):
        """Clear stored tokens (logout)."""
        if "default" in stored_tokens:
            del stored_tokens["default"]


# Singleton instance
amazon_oauth = AmazonOAuth()
