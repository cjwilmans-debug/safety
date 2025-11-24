"""
Amazon Seller Central OAuth Handler

Handles the OAuth 2.0 flow for Amazon's Selling Partner API.
Users click to authorize, and we get the refresh token.
"""

import secrets
import requests
from urllib.parse import urlencode


class AmazonOAuth:
    """Handle Amazon SP-API OAuth flow."""

    # Amazon OAuth endpoints
    AUTHORIZE_URL = "https://sellercentral.amazon.com/apps/authorize/consent"
    TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    def __init__(self, app_id: str, client_secret: str):
        """
        Initialize OAuth handler.

        Args:
            app_id: LWA (Login with Amazon) App ID
            client_secret: LWA Client Secret
        """
        self.app_id = app_id
        self.client_secret = client_secret

    def get_authorization_url(self, redirect_uri: str, marketplace: str = "US") -> tuple:
        """
        Generate the authorization URL for the user to click.

        Args:
            redirect_uri: Where Amazon should redirect after authorization
            marketplace: Which marketplace to authorize (US, CA, MX, etc.)

        Returns:
            Tuple of (authorization_url, state)
        """
        state = secrets.token_urlsafe(32)

        params = {
            'application_id': self.app_id,
            'state': state,
            'redirect_uri': redirect_uri,
            'version': 'beta'  # Required for SP-API
        }

        url = f"{self.AUTHORIZE_URL}?{urlencode(params)}"
        return url, state

    def exchange_code_for_tokens(self, authorization_code: str, redirect_uri: str) -> dict:
        """
        Exchange the authorization code for access and refresh tokens.

        Args:
            authorization_code: The code from Amazon's callback
            redirect_uri: Must match the one used in authorization

        Returns:
            Dictionary with access_token and refresh_token, or None on failure
        """
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': redirect_uri,
            'client_id': self.app_id,
            'client_secret': self.client_secret
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Token exchange failed: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Get a new access token using the refresh token.

        Args:
            refresh_token: The stored refresh token

        Returns:
            Dictionary with new access_token, or None on failure
        """
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.app_id,
            'client_secret': self.client_secret
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Token refresh failed: {e}")
            return None
