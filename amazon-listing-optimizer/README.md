# Amazon Listing Optimizer

A web-based application for connecting to Amazon Seller Central via OAuth and analyzing product listings for optimization opportunities.

Built for **The Gr1nds** brand.

## Features

- **OAuth 2.0 Integration**: Secure popup-based authentication with Amazon Seller Central
- **Listing Analysis**: Automated scoring and recommendations for:
  - Title optimization
  - Image stack assessment
  - Bullet point effectiveness
- **Multi-Marketplace Support**: US, CA, UK, DE, and 12+ other Amazon marketplaces
- **API Endpoints**: RESTful API for integration with other tools
- **Real-time Dashboard**: View connection status and analyze listings

## Quick Start

### Prerequisites

- Python 3.10+
- Amazon Seller Central Professional Account
- Amazon SP-API Developer Registration

### 1. Clone and Install

```bash
cd amazon-listing-optimizer
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Amazon SP-API Credentials

#### Step 2a: Register as a Developer

1. Go to [Seller Central](https://sellercentral.amazon.com/)
2. Navigate to **Apps & Services** → **Develop Apps**
3. Complete the Developer Registration if not already done

#### Step 2b: Create an App

1. In Developer Central, click **Add new app client**
2. Fill in:
   - **App name**: "Listing Optimizer" (or your choice)
   - **API Type**: SP-API
   - **OAuth Redirect URI**: `http://localhost:8000/oauth/callback`
3. Note your **LWA Client ID** and **LWA Client Secret**

#### Step 2c: Configure IAM (if using roles)

For advanced setups, create an IAM role with SP-API permissions. See [Amazon SP-API Documentation](https://developer-docs.amazon.com/sp-api/docs/creating-and-configuring-iam-policies-and-entities).

### 3. Set Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
LWA_CLIENT_ID=amzn1.application-oa2-client.xxxxxxxx
LWA_CLIENT_SECRET=your-secret-here
SP_API_APP_ID=amzn1.sp.solution.xxxxxxxx
OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback
APP_SECRET_KEY=generate-a-random-string-here
```

### 4. Run the Application

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the run script
python -m app.main
```

### 5. Connect to Amazon

1. Open `http://localhost:8000` in your browser
2. Select your marketplace (US, CA, UK, etc.)
3. Click **"Connect with Amazon"**
4. A popup will open for Amazon authorization
5. Log in and authorize the application
6. You're connected!

## API Reference

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/oauth/authorize` | GET | Initiates OAuth flow |
| `/oauth/callback` | GET | OAuth redirect handler |
| `/oauth/disconnect` | POST | Clears stored tokens |
| `/oauth/refresh` | POST | Refreshes access token |

### Analysis Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/listings/analyze/{asin}` | GET | Analyze a listing |
| `/api/catalog/item/{asin}` | GET | Get raw catalog data |
| `/api/catalog/search` | GET | Search catalog |
| `/api/status` | GET | Check connection status |

### Query Parameters

- `marketplace`: Marketplace code (US, CA, UK, etc.)
- `keywords`: Search keywords (for search endpoint)
- `brand`: Filter by brand name

## Example Usage

### Analyze a Listing

```bash
curl "http://localhost:8000/api/listings/analyze/B08N5WRWNW?marketplace=US"
```

Response:
```json
{
  "asin": "B08N5WRWNW",
  "marketplace": "US",
  "scores": {
    "title": {"score": 75, "issues": [], "recommendations": []},
    "images": {"score": 80, "issues": [], "image_count": 7},
    "bullets": {"score": 65, "issues": ["Bullet 3 is too short"]},
    "overall": 73.3
  }
}
```

### Search Catalog

```bash
curl "http://localhost:8000/api/catalog/search?keywords=coffee%20grinder&marketplace=US"
```

## Project Structure

```
amazon-listing-optimizer/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration settings
│   ├── oauth.py          # Amazon OAuth handler
│   └── sp_api_client.py  # SP-API client & analyzer
├── templates/
│   ├── index.html        # Main dashboard
│   └── callback.html     # OAuth callback page
├── frontend/
│   └── static/           # Static assets
├── .env.example          # Environment template
├── requirements.txt      # Python dependencies
└── README.md
```

## Troubleshooting

### "Application not configured" Error

Make sure your `.env` file exists and contains valid `LWA_CLIENT_ID` and `LWA_CLIENT_SECRET`.

### OAuth Popup Blocked

Ensure your browser allows popups for localhost.

### "Invalid redirect_uri" from Amazon

The redirect URI in your Amazon App settings must exactly match `OAUTH_REDIRECT_URI` in your `.env` file.

### Token Expired Errors

Click "Refresh Token" in the dashboard, or the app will automatically refresh when making API calls.

## Production Deployment

For production:

1. Use HTTPS (required by Amazon for OAuth)
2. Store tokens securely (Redis, database, or encrypted storage)
3. Set a strong `APP_SECRET_KEY`
4. Configure proper CORS settings
5. Use environment-specific OAuth redirect URIs

## License

Private - Built for The Gr1nds

## Support

For issues or questions, contact your Amazon Marketplace Specialist.
