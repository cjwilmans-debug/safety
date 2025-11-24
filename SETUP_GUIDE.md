# Amazon Seller Central to Dynamics 365 Integration

A web-based integration that syncs shipped orders from Amazon to Microsoft Dynamics 365 Business Central.

## What This Does

When orders ship on Amazon, this integration:
1. Fetches order details (SKUs, quantities, prices, customer info)
2. Creates sales invoices (or sales orders) in Dynamics 365
3. Tracks processed orders to prevent duplicates
4. Runs automatically on a schedule (optional)

## Features

- **Web-based UI** - No command line needed
- **OAuth Login** - Click to authorize, no API keys to copy
- **Dashboard** - See sync status at a glance
- **Auto-sync** - Set it and forget it
- **Order History** - Track all synced orders

## Prerequisites

- Python 3.8 or higher
- Amazon Seller Central account
- Microsoft Dynamics 365 Business Central subscription
- Azure Active Directory (comes with D365)

## Quick Start

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start the Web App

```bash
python app.py
```

Open your browser to: **http://localhost:5000**

### Step 3: Connect Amazon

1. Click **Setup** in the sidebar
2. In the Amazon section, you'll need your **LWA App ID** and **Client Secret**
3. Click **Connect to Amazon**
4. Log into your Seller Central account and authorize the app

### Step 4: Connect Dynamics 365

1. In the Dynamics 365 section, enter your Azure AD credentials
2. Click **Connect to Dynamics 365**
3. Log into your Microsoft account and authorize
4. Select your company

### Step 5: Sync Orders

1. Go to the **Dashboard**
2. Click **Sync Now**
3. Choose how many days to look back
4. Watch your orders flow into Dynamics 365!

---

## Detailed Setup Instructions

### Amazon Seller Central Setup

Before connecting, you need to create an app in Amazon:

1. Go to [Seller Central](https://sellercentral.amazon.com)
2. Navigate to **Apps & Services** > **Develop Apps**
3. Click **Add new app client**
4. Fill in the app details:
   - App name: "Dynamics 365 Integration" (or whatever you prefer)
   - API Type: SP-API
5. After creating, note your:
   - **LWA Client ID** (looks like `amzn1.application-oa2-client.xxxxx`)
   - **LWA Client Secret**
6. Under **OAuth redirect URIs**, add:
   ```
   http://localhost:5000/callback/amazon
   ```
   (Use your actual domain in production)

### Microsoft Dynamics 365 / Azure AD Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Fill in:
   - Name: "Amazon Integration"
   - Supported account types: Single tenant
   - Redirect URI: Web - `http://localhost:5000/callback/dynamics`
5. After creating, note your:
   - **Application (client) ID**
   - **Directory (tenant) ID**
6. Go to **Certificates & secrets** > **New client secret**
   - Save the **Secret Value** immediately (it won't show again!)
7. Go to **API permissions** > **Add a permission**
   - Select **APIs my organization uses**
   - Search for "Dynamics 365 Business Central"
   - Add **Financials.ReadWrite.All**
   - Click **Grant admin consent**

---

## Running in Production

### Using Gunicorn (Linux)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:
```bash
docker build -t amazon-dynamics .
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance amazon-dynamics
```

### Environment Variables

For production, set these environment variables:

```bash
export SECRET_KEY="your-secret-key-here"
export FLASK_ENV=production
```

---

## Marketplace IDs

If you sell in multiple marketplaces, here are the IDs:

| Marketplace | ID |
|------------|-----|
| US | ATVPDKIKX0DER |
| Canada | A2EUQ1WTGCTBG2 |
| Mexico | A1AM78C64UM0Y8 |
| UK | A1F83G8C2ARO7P |
| Germany | A1PA6795UKMFR9 |
| France | A13V1IB3VIYBER |
| Italy | APJ6JRA9NG5V4 |
| Spain | A1RKKUPIHCS9HS |

---

## Troubleshooting

### "Authorization failed" from Amazon

- Make sure your OAuth redirect URI in Seller Central matches exactly
- Check that your app is approved and not in draft status

### "401 Unauthorized" from Dynamics 365

- Verify admin consent was granted for API permissions
- Check that your client secret hasn't expired
- Make sure you're using the correct tenant ID

### Orders not syncing

- Only "Shipped" orders are synced
- Check the Logs page for error details
- Verify your items exist in Dynamics 365 (or they'll sync with descriptions only)

### Can't select company

- Make sure your Azure AD app has the correct permissions
- Try disconnecting and reconnecting Dynamics 365

---

## Files & Data

| File/Folder | Purpose |
|-------------|---------|
| `app.py` | Main web application |
| `instance/integration.db` | SQLite database with tokens and order history |
| `templates/` | HTML templates for the web UI |

---

## Security Notes

- Tokens are stored in a local SQLite database
- For production, use HTTPS
- Set a strong `SECRET_KEY` environment variable
- The database file contains sensitive tokens - protect it accordingly
