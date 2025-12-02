"""
Configuration settings for the Amazon Listing Optimizer app.
Loads settings from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LWA (Login with Amazon) OAuth Credentials
    lwa_client_id: str = ""
    lwa_client_secret: str = ""

    # SP-API App ID
    sp_api_app_id: str = ""

    # AWS IAM Role ARN for SP-API
    aws_role_arn: str = ""

    # Application Settings
    app_secret_key: str = "change-this-in-production"
    app_base_url: str = "http://localhost:8000"
    oauth_redirect_uri: str = "http://localhost:8000/oauth/callback"

    # Default Marketplace
    default_marketplace: str = "US"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Amazon LWA OAuth Endpoints
class AmazonOAuthConfig:
    """Amazon Login with Amazon OAuth configuration."""

    # OAuth Authorization Endpoint
    AUTHORIZE_URL = "https://www.amazon.com/ap/oa"

    # Token Exchange Endpoint
    TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    # Required OAuth Scopes for SP-API
    SCOPES = [
        "sellingpartnerapi::migration",  # For SP-API access
    ]

    # SP-API Endpoints by Region
    ENDPOINTS = {
        "NA": "https://sellingpartnerapi-na.amazon.com",  # US, CA, MX, BR
        "EU": "https://sellingpartnerapi-eu.amazon.com",  # UK, DE, FR, IT, ES, etc.
        "FE": "https://sellingpartnerapi-fe.amazon.com",  # JP, AU, SG
    }

    # Marketplace IDs
    MARKETPLACE_IDS = {
        "US": "ATVPDKIKX0DER",
        "CA": "A2EUQ1WTGCTBG2",
        "MX": "A1AM78C64UM0Y8",
        "BR": "A2Q3Y263D00KWC",
        "UK": "A1F83G8C2ARO7P",
        "DE": "A1PA6795UKMFR9",
        "FR": "A13V1IB3VIYBER",
        "IT": "APJ6JRA9NG5V4",
        "ES": "A1RKKUPIHCS9HS",
        "NL": "A1805IZSGTT6HS",
        "SE": "A2NODRKZP88ZB9",
        "PL": "A1C3SOZRARQ6R3",
        "JP": "A1VC38T7YXB528",
        "AU": "A39IBJ37TRP1C6",
        "SG": "A19VAU5U5O7RUS",
        "IN": "A21TJRUUN4KGV",
    }

    @classmethod
    def get_region_for_marketplace(cls, marketplace: str) -> str:
        """Get the API region for a given marketplace."""
        na_marketplaces = ["US", "CA", "MX", "BR"]
        fe_marketplaces = ["JP", "AU", "SG"]

        if marketplace in na_marketplaces:
            return "NA"
        elif marketplace in fe_marketplaces:
            return "FE"
        else:
            return "EU"

    @classmethod
    def get_endpoint(cls, marketplace: str) -> str:
        """Get the SP-API endpoint URL for a given marketplace."""
        region = cls.get_region_for_marketplace(marketplace)
        return cls.ENDPOINTS[region]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
