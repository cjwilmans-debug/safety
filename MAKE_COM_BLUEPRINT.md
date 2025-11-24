# Make.com Blueprint: Amazon Seller Central → Dynamics 365

This blueprint automates syncing shipped orders from Amazon to Dynamics 365 Business Central.

---

## Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TRIGGER       │───▶│   GET ORDER     │───▶│   ROUTER        │───▶│  CREATE IN D365 │
│ Schedule/Webhook│    │   DETAILS       │    │ (Filter Shipped)│    │  Sales Invoice  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Step 1: Create New Scenario

1. Log into [Make.com](https://make.com)
2. Click **Create a new scenario**
3. Name it: `Amazon to Dynamics 365 - Order Sync`

---

## Step 2: Add Trigger Module - Daily End of Day

**Module:** `Schedule`

| Field | Value |
|-------|-------|
| Run scenario | `Every day` |
| Time | `11:55 PM` (or `23:55`) |
| Time zone | `America/Los_Angeles` *(or your timezone)* |

This runs once per day at end of day, capturing all shipped orders from that day.

**Alternative times:**
- `11:55 PM` - Just before midnight (recommended)
- `12:00 AM` - Midnight (start of next day)
- `6:00 AM` - Early morning (catches overnight processing)

---

## Step 3: Create Amazon Connection

When prompted to create a connection:

| Field | What to Enter |
|-------|---------------|
| **Connection name** | `Legendary Foods Amazon` |
| **Client ID** | Your LWA App Client ID from Seller Central |
| **Client Secret** | Your LWA Client Secret |
| **Marketplace** | `North America` |

**To get these credentials:**
1. Go to [Seller Central](https://sellercentral.amazon.com)
2. Navigate to **Apps & Services** → **Develop Apps**
3. Click **Add new app client**
4. Copy the **LWA credentials**

After entering, click **Sign in with Amazon** and authorize.

---

## Step 4: Add "List Orders" Module

**Module:** `Amazon Seller Central` → `List Orders`

| Field | Value |
|-------|-------|
| Connection | `Legendary Foods Amazon` |
| Marketplace IDs | `ATVPDKIKX0DER` (US) |
| Order Statuses | `Shipped` |
| Created After | `{{addDays(now; -1)}}` *(last 24 hours)* |
| Limit | `100` |

---

## Step 5: Add Iterator

**Module:** `Flow Control` → `Iterator`

| Field | Value |
|-------|-------|
| Array | `{{2.Orders}}` *(output from List Orders)* |

---

## Step 6: Add "Get Order Items" Module

**Module:** `Amazon Seller Central` → `Get Order Items`

| Field | Value |
|-------|-------|
| Connection | `Legendary Foods Amazon` |
| Order ID | `{{3.AmazonOrderId}}` |

---

## Step 7: Create Dynamics 365 Connection

**Module:** `Microsoft Dynamics 365 Business Central` → Create connection

| Field | What to Enter |
|-------|---------------|
| **Connection name** | `Legendary Foods D365` |
| **Environment** | `Production` or `Sandbox` |
| **Company ID** | Your D365 Company GUID |

**Authentication:** Click **Sign in with Microsoft** and log in with your D365 admin account.

**To find Company ID:**
1. Log into Business Central
2. Go to **Settings** → **Company Information**
3. Or use the API: The ID is in the URL when you access your company

---

## Step 8: Add Router (Optional - for filtering)

**Module:** `Flow Control` → `Router`

Add a filter on the route:
| Field | Value |
|-------|-------|
| Label | `Only Shipped Orders` |
| Condition | `{{3.OrderStatus}}` **equals** `Shipped` |

---

## Step 9: Add "Create Sales Invoice" Module

**Module:** `Microsoft Dynamics 365 Business Central` → `Create a Record`

| Field | Value |
|-------|-------|
| Connection | `Legendary Foods D365` |
| Record Type | `Sales Invoices` |

### Sales Invoice Header Fields:

| Field | Value/Mapping |
|-------|---------------|
| **Customer Number** | `AMAZON-CUSTOMER` *(or map dynamically)* |
| **External Document Number** | `{{3.AmazonOrderId}}` |
| **Document Date** | `{{3.PurchaseDate}}` |
| **Currency Code** | `USD` |

---

## Step 10: Add Iterator for Line Items

**Module:** `Flow Control` → `Iterator`

| Field | Value |
|-------|-------|
| Array | `{{4.OrderItems}}` |

---

## Step 11: Add "Create Sales Invoice Line" Module

**Module:** `Microsoft Dynamics 365 Business Central` → `Create a Record`

| Field | Value |
|-------|-------|
| Connection | `Legendary Foods D365` |
| Record Type | `Sales Invoice Lines` |

### Sales Invoice Line Fields:

| Field | Value/Mapping |
|-------|---------------|
| **Document ID** | `{{9.id}}` *(from Create Invoice)* |
| **Item Number** | `{{10.SellerSKU}}` |
| **Description** | `{{10.Title}}` |
| **Quantity** | `{{10.QuantityShipped}}` |
| **Unit Price** | `{{10.ItemPrice.Amount / 10.QuantityShipped}}` |

---

## Step 12: Add Error Handling

Right-click on the D365 module and add:

**Module:** `Tools` → `Set Variable`

| Field | Value |
|-------|-------|
| Variable name | `FailedOrders` |
| Value | `{{3.AmazonOrderId}}` |

---

## Step 13: Add Completion Notification (Optional)

**Module:** `Email` → `Send an Email`

| Field | Value |
|-------|-------|
| To | `your-email@legendaryfoods.com` |
| Subject | `Amazon Sync Complete - {{formatDate(now; "YYYY-MM-DD")}}` |
| Content | `Synced {{length(2.Orders)}} orders to Dynamics 365` |

---

## Complete Module Sequence

```
1. Schedule (Daily at 11:55 PM)
      ↓
2. Amazon: List Orders (Shipped, last 24h)
      ↓
3. Iterator (Orders array)
      ↓
4. Amazon: Get Order Items
      ↓
5. Router (Filter: Only Shipped)
      ↓
6. D365: Create Sales Invoice
      ↓
7. Iterator (Order Items array)
      ↓
8. D365: Create Sales Invoice Line
      ↓
9. Email: Send Summary (optional)
```

---

## Field Reference: Amazon Order Data

These fields are available after the "List Orders" module:

| Field | Description | Example |
|-------|-------------|---------|
| `AmazonOrderId` | Unique order ID | `111-1234567-1234567` |
| `PurchaseDate` | When order was placed | `2024-01-15T10:30:00Z` |
| `OrderStatus` | Current status | `Shipped` |
| `OrderTotal.Amount` | Total order amount | `49.99` |
| `OrderTotal.CurrencyCode` | Currency | `USD` |
| `ShippingAddress.Name` | Customer name | `John Smith` |
| `ShippingAddress.AddressLine1` | Street address | `123 Main St` |
| `ShippingAddress.City` | City | `Los Angeles` |
| `ShippingAddress.StateOrRegion` | State | `CA` |
| `ShippingAddress.PostalCode` | Zip code | `90210` |
| `BuyerInfo.BuyerEmail` | Customer email | `john@email.com` |

---

## Field Reference: Amazon Order Items

These fields are available after "Get Order Items":

| Field | Description | Example |
|-------|-------------|---------|
| `SellerSKU` | Your SKU | `LF-PROTEIN-BAR-12` |
| `ASIN` | Amazon product ID | `B08XYZ1234` |
| `Title` | Product title | `Legendary Foods Protein Bar` |
| `QuantityShipped` | Units shipped | `2` |
| `ItemPrice.Amount` | Line total | `29.98` |
| `ItemPrice.CurrencyCode` | Currency | `USD` |

---

## Field Reference: Dynamics 365 Sales Invoice

Required fields when creating:

| Field | Required | Description |
|-------|----------|-------------|
| `customerNumber` | Yes | Customer account number |
| `externalDocumentNumber` | No | Amazon Order ID (for reference) |
| `invoiceDate` | Yes | Invoice date |
| `currencyCode` | No | Currency (defaults to company) |

---

## Field Reference: Dynamics 365 Invoice Lines

Required fields when creating lines:

| Field | Required | Description |
|-------|----------|-------------|
| `documentId` | Yes | Parent invoice ID |
| `itemNumber` | Yes* | Item SKU (must match D365 item) |
| `description` | No | Line description |
| `quantity` | Yes | Number of units |
| `unitPrice` | Yes | Price per unit |

*If item doesn't exist, use `description` with `type: "Comment"`

---

## Pre-Requisites Checklist

### Amazon Seller Central
- [ ] Developer account registered
- [ ] App created in Develop Apps
- [ ] LWA Client ID copied
- [ ] LWA Client Secret copied
- [ ] OAuth Redirect URI set to: `https://www.integromat.com/oauth/cb/amazon-seller`

### Dynamics 365 Business Central
- [ ] Admin access to D365
- [ ] Company ID identified
- [ ] "Amazon Customer" created (or customer mapping strategy)
- [ ] Items/SKUs exist in D365 (matching Amazon SKUs)

### Make.com
- [ ] Make.com account created
- [ ] Appropriate plan (Operations limit covers your volume)

---

## Estimated Operations Usage

Per sync cycle:
- 1 operation: Schedule trigger
- 1 operation: List Orders
- N operations: Get Order Items (N = number of orders)
- N operations: Create Invoice
- M operations: Create Invoice Lines (M = total line items)

**Example:** 50 orders with 2 items each = ~1 + 1 + 50 + 50 + 100 = **~202 operations per sync**

---

## Testing Checklist

1. [ ] Run scenario manually first
2. [ ] Verify orders appear in D365
3. [ ] Check line items have correct SKUs and prices
4. [ ] Confirm no duplicate orders created
5. [ ] Enable scheduling after testing

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid credentials" on Amazon | Re-authorize connection, check LWA credentials |
| "Customer not found" in D365 | Create "AMAZON-CUSTOMER" in D365 first |
| "Item not found" in D365 | Map SKUs or use description-only lines |
| Duplicate orders | Add a filter checking `externalDocumentNumber` |
| Rate limiting | Add delay modules between API calls |
