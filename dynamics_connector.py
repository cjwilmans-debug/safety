"""
Microsoft Dynamics 365 Business Central API Connector
Creates sales orders and invoices from Amazon order data
"""

import requests
import msal
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class DynamicsConnector:
    """Connects to Dynamics 365 Business Central to create sales orders and invoices."""

    def __init__(self, config: dict):
        """
        Initialize with Dynamics 365 credentials.

        Args:
            config: Dictionary containing Dynamics 365 API credentials
        """
        self.tenant_id = config['tenant_id']
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.environment = config['environment']
        self.company_id = config['company_id']

        self.base_url = f"https://api.businesscentral.dynamics.com/v2.0/{self.tenant_id}/{self.environment}/api/v2.0"
        self.token = None
        self.token_expiry = None

        # Cache for customer and item lookups
        self._customer_cache = {}
        self._item_cache = {}

    def _get_access_token(self) -> str:
        """Get OAuth2 access token for Dynamics 365 API."""
        if self.token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return self.token

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        scope = ["https://api.businesscentral.dynamics.com/.default"]

        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential=self.client_secret
        )

        result = app.acquire_token_for_client(scopes=scope)

        if "access_token" in result:
            self.token = result["access_token"]
            # Token typically valid for 1 hour, refresh a bit earlier
            from datetime import timedelta
            self.token_expiry = datetime.utcnow() + timedelta(minutes=55)
            return self.token
        else:
            error = result.get("error_description", "Unknown error")
            raise Exception(f"Failed to get access token: {error}")

    def _get_headers(self) -> dict:
        """Get HTTP headers with authorization."""
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an API request to Dynamics 365."""
        url = f"{self.base_url}/companies({self.company_id})/{endpoint}"
        headers = self._get_headers()

        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json() if response.text else {}

        except requests.exceptions.HTTPError as e:
            logger.error(f"Dynamics API error: {e.response.text}")
            raise

    def find_or_create_customer(self, customer_name: str, email: str = "", address: dict = None) -> str:
        """
        Find existing customer or create new one.

        Args:
            customer_name: Customer display name
            email: Customer email
            address: Address dictionary

        Returns:
            Customer ID
        """
        # Check cache first
        cache_key = f"{customer_name}_{email}"
        if cache_key in self._customer_cache:
            return self._customer_cache[cache_key]

        # Search for existing customer
        search_name = customer_name.replace("'", "''")  # Escape single quotes
        endpoint = f"customers?$filter=displayName eq '{search_name}'"

        try:
            result = self._make_request("GET", endpoint)
            customers = result.get("value", [])

            if customers:
                customer_id = customers[0]["id"]
                self._customer_cache[cache_key] = customer_id
                return customer_id
        except Exception as e:
            logger.warning(f"Error searching for customer: {e}")

        # Create new customer
        customer_data = {
            "displayName": customer_name,
            "type": "Company",
            "email": email
        }

        if address:
            customer_data.update({
                "addressLine1": address.get("address_line_1", ""),
                "addressLine2": address.get("address_line_2", ""),
                "city": address.get("city", ""),
                "state": address.get("state", ""),
                "postalCode": address.get("postal_code", ""),
                "country": address.get("country", "")
            })

        result = self._make_request("POST", "customers", customer_data)
        customer_id = result["id"]
        self._customer_cache[cache_key] = customer_id
        logger.info(f"Created new customer: {customer_name} ({customer_id})")
        return customer_id

    def find_item_by_sku(self, sku: str) -> Optional[dict]:
        """
        Find an item by SKU/item number.

        Args:
            sku: The SKU/item number to search for

        Returns:
            Item dictionary or None if not found
        """
        if sku in self._item_cache:
            return self._item_cache[sku]

        endpoint = f"items?$filter=number eq '{sku}'"

        try:
            result = self._make_request("GET", endpoint)
            items = result.get("value", [])

            if items:
                self._item_cache[sku] = items[0]
                return items[0]
        except Exception as e:
            logger.warning(f"Error finding item {sku}: {e}")

        return None

    def create_sales_order(self, amazon_order: dict) -> dict:
        """
        Create a sales order in Dynamics 365 from Amazon order data.

        Args:
            amazon_order: Order dictionary from AmazonConnector

        Returns:
            Created sales order data
        """
        # Get or create customer
        customer_name = amazon_order['shipping_address'].get('name', 'Amazon Customer')
        if not customer_name:
            customer_name = 'Amazon Customer'

        customer_id = self.find_or_create_customer(
            customer_name=customer_name,
            email=amazon_order.get('buyer_email', ''),
            address=amazon_order.get('shipping_address')
        )

        # Parse order date
        order_date = amazon_order.get('purchase_date', '')
        if order_date:
            try:
                order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                order_date = order_date.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                order_date = datetime.utcnow().strftime('%Y-%m-%d')
        else:
            order_date = datetime.utcnow().strftime('%Y-%m-%d')

        # Create sales order header
        order_data = {
            "customerId": customer_id,
            "orderDate": order_date,
            "externalDocumentNumber": amazon_order['order_id'],
            "currencyCode": amazon_order.get('currency', 'USD')
        }

        result = self._make_request("POST", "salesOrders", order_data)
        sales_order_id = result["id"]
        logger.info(f"Created sales order {result.get('number', '')} for Amazon order {amazon_order['order_id']}")

        # Add line items
        for item in amazon_order.get('line_items', []):
            self._add_sales_order_line(sales_order_id, item)

        return result

    def _add_sales_order_line(self, sales_order_id: str, line_item: dict):
        """Add a line item to a sales order."""
        sku = line_item.get('sku', '')

        # Find the item in Dynamics
        dynamics_item = self.find_item_by_sku(sku)

        line_data = {
            "quantity": line_item.get('quantity', 1),
            "unitPrice": line_item.get('unit_price', 0)
        }

        if dynamics_item:
            line_data["itemId"] = dynamics_item["id"]
        else:
            # If item not found, use description
            line_data["description"] = f"{sku} - {line_item.get('title', 'Amazon Item')}"
            logger.warning(f"Item {sku} not found in Dynamics, using description")

        endpoint = f"salesOrders({sales_order_id})/salesOrderLines"
        self._make_request("POST", endpoint, line_data)

    def create_sales_invoice(self, amazon_order: dict) -> dict:
        """
        Create a sales invoice in Dynamics 365 from Amazon order data.

        Args:
            amazon_order: Order dictionary from AmazonConnector

        Returns:
            Created sales invoice data
        """
        # Get or create customer
        customer_name = amazon_order['shipping_address'].get('name', 'Amazon Customer')
        if not customer_name:
            customer_name = 'Amazon Customer'

        customer_id = self.find_or_create_customer(
            customer_name=customer_name,
            email=amazon_order.get('buyer_email', ''),
            address=amazon_order.get('shipping_address')
        )

        # Parse order date
        order_date = amazon_order.get('purchase_date', '')
        if order_date:
            try:
                order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                order_date = order_date.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                order_date = datetime.utcnow().strftime('%Y-%m-%d')
        else:
            order_date = datetime.utcnow().strftime('%Y-%m-%d')

        # Create sales invoice header
        invoice_data = {
            "customerId": customer_id,
            "invoiceDate": order_date,
            "externalDocumentNumber": amazon_order['order_id'],
            "currencyCode": amazon_order.get('currency', 'USD')
        }

        result = self._make_request("POST", "salesInvoices", invoice_data)
        invoice_id = result["id"]
        logger.info(f"Created sales invoice {result.get('number', '')} for Amazon order {amazon_order['order_id']}")

        # Add line items
        for item in amazon_order.get('line_items', []):
            self._add_sales_invoice_line(invoice_id, item)

        return result

    def _add_sales_invoice_line(self, invoice_id: str, line_item: dict):
        """Add a line item to a sales invoice."""
        sku = line_item.get('sku', '')

        # Find the item in Dynamics
        dynamics_item = self.find_item_by_sku(sku)

        line_data = {
            "quantity": line_item.get('quantity', 1),
            "unitPrice": line_item.get('unit_price', 0)
        }

        if dynamics_item:
            line_data["itemId"] = dynamics_item["id"]
        else:
            line_data["description"] = f"{sku} - {line_item.get('title', 'Amazon Item')}"
            logger.warning(f"Item {sku} not found in Dynamics, using description")

        endpoint = f"salesInvoices({invoice_id})/salesInvoiceLines"
        self._make_request("POST", endpoint, line_data)

    def check_order_exists(self, amazon_order_id: str) -> bool:
        """
        Check if an Amazon order has already been imported.

        Args:
            amazon_order_id: The Amazon order ID

        Returns:
            True if order exists, False otherwise
        """
        # Check sales orders
        endpoint = f"salesOrders?$filter=externalDocumentNumber eq '{amazon_order_id}'"
        try:
            result = self._make_request("GET", endpoint)
            if result.get("value"):
                return True
        except Exception:
            pass

        # Check sales invoices
        endpoint = f"salesInvoices?$filter=externalDocumentNumber eq '{amazon_order_id}'"
        try:
            result = self._make_request("GET", endpoint)
            if result.get("value"):
                return True
        except Exception:
            pass

        return False


# Example usage
if __name__ == '__main__':
    import json

    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)

    connector = DynamicsConnector(config['dynamics365'])

    # Test with a sample order
    sample_order = {
        'order_id': 'TEST-123',
        'purchase_date': '2024-01-15T10:30:00Z',
        'shipping_address': {
            'name': 'Test Customer',
            'address_line_1': '123 Main St',
            'city': 'Anytown',
            'state': 'CA',
            'postal_code': '90210',
            'country': 'US'
        },
        'buyer_email': 'test@example.com',
        'line_items': [
            {
                'sku': 'TEST-SKU-001',
                'title': 'Test Product',
                'quantity': 2,
                'unit_price': 19.99,
                'total_price': 39.98,
                'currency': 'USD'
            }
        ],
        'total_amount': 39.98,
        'currency': 'USD'
    }

    # Check if order exists
    if not connector.check_order_exists('TEST-123'):
        invoice = connector.create_sales_invoice(sample_order)
        print(f"Created invoice: {invoice}")
