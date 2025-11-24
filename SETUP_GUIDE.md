# Amazon Seller Central to Dynamics 365 Integration

Automatically sync shipped orders from Amazon to Microsoft Dynamics 365 Business Central.

## What This Does

When orders ship on Amazon, this integration:
1. Fetches order details (SKUs, quantities, prices, customer info)
2. Creates a sales invoice (or sales order) in Dynamics 365
3. Tracks processed orders to prevent duplicates

## Prerequisites

- Python 3.8 or higher
- Amazon Seller Central account with SP-API access
- Microsoft Dynamics 365 Business Central subscription
- Azure Active Directory app registration

## Setup Instructions

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Amazon Seller Central SP-API Setup

1. **Register as a Developer**
   - Go to Seller Central > Apps & Services > Develop Apps
   - Click "Add new app client"
   - Note your **LWA App ID** and **LWA Client Secret**

2. **Create AWS IAM User**
   - Go to AWS Console > IAM
   - Create a new user with programmatic access
   - Note the **Access Key** and **Secret Key**
   - Create a role for the SP-API and note the **Role ARN**

3. **Get Refresh Token**
   - In your Seller Central app, authorize it for your marketplace
   - Complete the OAuth flow to get a **Refresh Token**

4. **Find Your Marketplace ID**
   Common marketplace IDs:
   - US: `ATVPDKIKX0DER`
   - Canada: `A2EUQ1WTGCTBG2`
   - UK: `A1F83G8C2ARO7P`
   - Germany: `A1PA6795UKMFR9`

### Step 3: Dynamics 365 Setup

1. **Register Azure AD Application**
   - Go to Azure Portal > Azure Active Directory > App registrations
   - Click "New registration"
   - Name it (e.g., "Amazon Integration")
   - Note the **Application (client) ID** and **Directory (tenant) ID**

2. **Create Client Secret**
   - In your app registration, go to Certificates & secrets
   - Create a new client secret
   - Note the **Secret Value** (save immediately, it won't show again!)

3. **Grant API Permissions**
   - In your app registration, go to API permissions
   - Add permission > APIs my organization uses
   - Search for "Dynamics 365 Business Central"
   - Add `Financials.ReadWrite.All` permission
   - Grant admin consent

4. **Get Company ID**
   - In Business Central, go to your company
   - The Company ID is in the URL or can be found via the API

5. **Get Environment Name**
   - This is typically "Production" or "Sandbox"
   - Found in Business Central admin center

### Step 4: Create Configuration File

1. Copy the template:
   ```bash
   cp config_template.json config.json
   ```

2. Edit `config.json` with your credentials:
   ```json
   {
       "amazon": {
           "refresh_token": "your-refresh-token",
           "lwa_app_id": "amzn1.application-oa2-client.xxx",
           "lwa_client_secret": "your-lwa-secret",
           "aws_access_key": "AKIA...",
           "aws_secret_key": "your-aws-secret",
           "role_arn": "arn:aws:iam::123456789:role/your-role",
           "marketplace_id": "ATVPDKIKX0DER"
       },
       "dynamics365": {
           "tenant_id": "your-azure-tenant-id",
           "client_id": "your-app-client-id",
           "client_secret": "your-client-secret",
           "environment": "Production",
           "company_id": "your-company-guid"
       },
       "settings": {
           "sync_interval_minutes": 60,
           "days_to_look_back": 1,
           "log_file": "integration.log"
       }
   }
   ```

## Usage

### Run Once (Manual Sync)
```bash
# Sync orders from the last day
python main.py

# Sync orders from a specific date
python main.py --date 2024-01-15

# Sync orders from last 7 days
python main.py --days-back 7

# Create sales orders instead of invoices
python main.py --sales-order

# Test without making changes (dry run)
python main.py --dry-run
```

### Run Continuously (Scheduled)
```bash
# Run every hour (configured in config.json)
python main.py --schedule
```

### Run as a Service (Windows)
Create a Windows Task Scheduler task to run the script periodically.

### Run as a Service (Linux)
Create a systemd service or cron job:
```bash
# Cron job every hour
0 * * * * cd /path/to/integration && python main.py >> /var/log/amazon-dynamics.log 2>&1
```

## Mapping Items

For best results, your SKUs in Amazon should match the Item Numbers in Dynamics 365.

If a SKU doesn't match, the integration will:
- Create a line item with the SKU in the description
- You may need to manually map these items

## Troubleshooting

### "Access Denied" from Amazon API
- Verify your refresh token hasn't expired
- Check that your app is authorized for the marketplace
- Ensure IAM role has correct permissions

### "401 Unauthorized" from Dynamics 365
- Check Azure AD app registration permissions
- Verify admin consent was granted
- Ensure client secret hasn't expired

### Orders Not Appearing
- Only "Shipped" orders are synced
- Check the `days_to_look_back` setting
- Review `integration.log` for errors

### Duplicate Orders
- The integration tracks processed orders in `processed_orders.json`
- It also checks Dynamics 365 for existing orders with the same Amazon Order ID

## Files Created

- `config.json` - Your configuration (keep secret!)
- `processed_orders.json` - Track of synced orders
- `integration.log` - Log file (if configured)

## Security Notes

- Never commit `config.json` to version control
- Store credentials securely
- Use environment variables in production
- Rotate secrets regularly
