"""
Amazon Listing Optimizer - Main FastAPI Application.
Provides OAuth integration with Amazon SP-API and listing analysis tools.
"""
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
import logging

from .config import get_settings, AmazonOAuthConfig
from .oauth import amazon_oauth, TokenData
from .sp_api_client import SPAPIClient, ListingAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Amazon Listing Optimizer",
    description="OAuth integration with Amazon SP-API for listing optimization",
    version="1.0.0",
)

# Setup templates and static files
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount static files
static_dir = BASE_DIR / "frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main dashboard page."""
    settings = get_settings()
    tokens = amazon_oauth.get_stored_tokens()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "is_connected": tokens is not None,
            "app_configured": bool(settings.lwa_client_id),
            "marketplaces": list(AmazonOAuthConfig.MARKETPLACE_IDS.keys()),
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/status")
async def get_connection_status():
    """Get the current Amazon connection status."""
    settings = get_settings()
    tokens = amazon_oauth.get_stored_tokens()

    return {
        "connected": tokens is not None,
        "app_configured": bool(settings.lwa_client_id and settings.lwa_client_secret),
        "token_expired": tokens.is_expired() if tokens else None,
        "marketplace": settings.default_marketplace,
    }


# ============================================================================
# OAuth Endpoints
# ============================================================================

@app.get("/oauth/authorize")
async def oauth_authorize(marketplace: str = Query(default="US")):
    """
    Initiate OAuth flow - redirects to Amazon login.
    This is what triggers the Amazon popup/redirect.
    """
    settings = get_settings()

    if not settings.lwa_client_id:
        raise HTTPException(
            status_code=400,
            detail="Application not configured. Please set LWA_CLIENT_ID in .env file.",
        )

    authorization_url, state = amazon_oauth.generate_authorization_url(marketplace)

    logger.info(f"OAuth initiated for marketplace: {marketplace}")
    logger.info(f"Redirecting to: {authorization_url}")

    return RedirectResponse(url=authorization_url)


@app.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    OAuth callback endpoint - Amazon redirects here after user authorization.
    """
    # Handle OAuth errors
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        return templates.TemplateResponse(
            "callback.html",
            {
                "request": request,
                "success": False,
                "error": error,
                "error_description": error_description,
            },
        )

    # Validate required parameters
    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail="Missing required parameters: code and state",
        )

    # Validate state (CSRF protection)
    oauth_state = amazon_oauth.validate_state(state)
    if not oauth_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired state parameter. Please try again.",
        )

    try:
        # Exchange code for tokens
        token_data = await amazon_oauth.exchange_code_for_tokens(code)

        logger.info(f"Successfully obtained tokens for marketplace: {oauth_state.marketplace}")

        return templates.TemplateResponse(
            "callback.html",
            {
                "request": request,
                "success": True,
                "marketplace": oauth_state.marketplace,
            },
        )

    except Exception as e:
        logger.error(f"Token exchange failed: {str(e)}")
        return templates.TemplateResponse(
            "callback.html",
            {
                "request": request,
                "success": False,
                "error": "token_exchange_failed",
                "error_description": str(e),
            },
        )


@app.post("/oauth/disconnect")
async def oauth_disconnect():
    """Disconnect from Amazon (clear stored tokens)."""
    amazon_oauth.clear_tokens()
    return {"success": True, "message": "Disconnected from Amazon"}


@app.post("/oauth/refresh")
async def oauth_refresh():
    """Manually refresh the access token."""
    tokens = amazon_oauth.get_stored_tokens()

    if not tokens:
        raise HTTPException(status_code=401, detail="Not connected to Amazon")

    try:
        new_tokens = await amazon_oauth.refresh_access_token(tokens.refresh_token)
        return {
            "success": True,
            "expires_at": new_tokens.expires_at.isoformat() if new_tokens.expires_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")


# ============================================================================
# Listing Analysis Endpoints
# ============================================================================

@app.get("/api/listings/analyze/{asin}")
async def analyze_listing(asin: str, marketplace: str = Query(default="US")):
    """
    Analyze a single listing by ASIN.
    Returns optimization scores and recommendations.
    """
    tokens = amazon_oauth.get_stored_tokens()
    if not tokens:
        raise HTTPException(status_code=401, detail="Not connected to Amazon. Please authorize first.")

    try:
        analyzer = ListingAnalyzer(marketplace)
        analysis = await analyzer.analyze_listing(asin)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/catalog/item/{asin}")
async def get_catalog_item(asin: str, marketplace: str = Query(default="US")):
    """
    Get raw catalog data for an ASIN.
    """
    tokens = amazon_oauth.get_stored_tokens()
    if not tokens:
        raise HTTPException(status_code=401, detail="Not connected to Amazon. Please authorize first.")

    try:
        client = SPAPIClient(marketplace)
        data = await client.get_catalog_item(asin)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch catalog item: {str(e)}")


@app.get("/api/catalog/search")
async def search_catalog(
    keywords: Optional[str] = None,
    brand: Optional[str] = None,
    marketplace: str = Query(default="US"),
    limit: int = Query(default=20, le=50),
):
    """
    Search the catalog for items.
    """
    tokens = amazon_oauth.get_stored_tokens()
    if not tokens:
        raise HTTPException(status_code=401, detail="Not connected to Amazon. Please authorize first.")

    try:
        client = SPAPIClient(marketplace)
        data = await client.search_catalog_items(
            keywords=keywords,
            brand_names=[brand] if brand else None,
            limit=limit,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ============================================================================
# Reports Endpoints
# ============================================================================

@app.post("/api/reports/create")
async def create_report(
    report_type: str = Query(..., description="Report type (e.g., GET_MERCHANT_LISTINGS_ALL_DATA)"),
    marketplace: str = Query(default="US"),
):
    """
    Create a report request.
    """
    tokens = amazon_oauth.get_stored_tokens()
    if not tokens:
        raise HTTPException(status_code=401, detail="Not connected to Amazon. Please authorize first.")

    try:
        client = SPAPIClient(marketplace)
        data = await client.create_report(report_type)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report creation failed: {str(e)}")


@app.get("/api/reports/{report_id}")
async def get_report_status(report_id: str, marketplace: str = Query(default="US")):
    """
    Get report status.
    """
    tokens = amazon_oauth.get_stored_tokens()
    if not tokens:
        raise HTTPException(status_code=401, detail="Not connected to Amazon. Please authorize first.")

    try:
        client = SPAPIClient(marketplace)
        data = await client.get_report(report_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report: {str(e)}")


# ============================================================================
# Configuration Endpoints
# ============================================================================

@app.get("/api/config/marketplaces")
async def get_marketplaces():
    """Get list of available marketplaces."""
    return {
        "marketplaces": [
            {"code": code, "marketplace_id": mid}
            for code, mid in AmazonOAuthConfig.MARKETPLACE_IDS.items()
        ]
    }


@app.get("/api/config/check")
async def check_configuration():
    """Check if the application is properly configured."""
    settings = get_settings()

    config_status = {
        "lwa_client_id": bool(settings.lwa_client_id),
        "lwa_client_secret": bool(settings.lwa_client_secret),
        "sp_api_app_id": bool(settings.sp_api_app_id),
        "aws_role_arn": bool(settings.aws_role_arn),
        "oauth_redirect_uri": settings.oauth_redirect_uri,
    }

    all_configured = all([
        config_status["lwa_client_id"],
        config_status["lwa_client_secret"],
    ])

    return {
        "configured": all_configured,
        "details": config_status,
        "message": "Ready to connect" if all_configured else "Missing required configuration",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
