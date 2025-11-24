"""
Microsoft Dynamics 365 Business Central OAuth Handler

Handles the OAuth 2.0 flow for Microsoft's Dynamics 365 API.
Users click to authorize with their Microsoft account.
"""

import secrets
import requests
from urllib.parse import urlencode


class DynamicsOAuth:
    """Handle Dynamics 365 OAuth flow."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        """
        Initialize OAuth handler.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD app client ID
            client_secret: Azure AD app client secret
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None

        # Microsoft OAuth endpoints
        self.authorize_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        # Dynamics 365 Business Central scope
        self.scope = "https://api.businesscentral.dynamics.com/.default offline_access"

    def get_authorization_url(self, redirect_uri: str) -> tuple:
        """
        Generate the authorization URL for the user to click.

        Args:
            redirect_uri: Where Microsoft should redirect after authorization

        Returns:
            Tuple of (authorization_url, state)
        """
        state = secrets.token_urlsafe(32)

        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'response_mode': 'query',
            'scope': self.scope,
            'state': state
        }

        url = f"{self.authorize_url}?{urlencode(params)}"
        return url, state

    def exchange_code_for_tokens(self, authorization_code: str, redirect_uri: str) -> dict:
        """
        Exchange the authorization code for access and refresh tokens.

        Args:
            authorization_code: The code from Microsoft's callback
            redirect_uri: Must match the one used in authorization

        Returns:
            Dictionary with access_token and refresh_token, or None on failure
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': redirect_uri,
            'scope': self.scope
        }

        try:
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Token exchange failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
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
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'scope': self.scope
        }

        try:
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Token refresh failed: {e}")
            return None

    def get_companies(self, environment: str = "Production") -> list:
        """
        Get list of companies in the Dynamics 365 environment.

        Args:
            environment: Environment name (Production, Sandbox, etc.)

        Returns:
            List of company dictionaries with id and name
        """
        if not self.access_token:
            return []

        url = f"https://api.businesscentral.dynamics.com/v2.0/{self.tenant_id}/{environment}/api/v2.0/companies"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return [{'id': c['id'], 'name': c['displayName']} for c in data.get('value', [])]
        except requests.exceptions.RequestException as e:
            print(f"Failed to get companies: {e}")
            return []
