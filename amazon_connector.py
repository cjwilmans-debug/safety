"""
Amazon Seller Central API Connector
Fetches shipped orders with SKU, units, and monetary values
"""

from sp_api.api import Orders, Reports
from sp_api.base import Marketplaces, SellingApiException
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import logging

logger = logging.getLogger(__name__)


class AmazonConnector:
    """Connects to Amazon Seller Central SP-API to fetch shipped order data."""

    def __init__(self, config: dict):
        """
        Initialize with Amazon SP-API credentials.

        Works with OAuth tokens obtained through the web authorization flow.
        No AWS credentials needed when using OAuth.

        Args:
            config: Dictionary containing Amazon API credentials
        """
        # Build credentials dict - AWS keys are optional with OAuth flow
        self.credentials = {
            'refresh_token': config['refresh_token'],
            'lwa_app_id': config['lwa_app_id'],
            'lwa_client_secret': config['lwa_client_secret'],
        }

        # Add AWS credentials only if provided (for backwards compatibility)
        if config.get('aws_access_key'):
            self.credentials['aws_access_key'] = config['aws_access_key']
        if config.get('aws_secret_key'):
            self.credentials['aws_secret_key'] = config['aws_secret_key']
        if config.get('role_arn'):
            self.credentials['role_arn'] = config['role_arn']

        self.marketplace_id = config.get('marketplace_id', 'ATVPDKIKX0DER')
        self._set_marketplace()

    def _set_marketplace(self):
        """Set the marketplace based on marketplace_id."""
        marketplace_map = {
            'ATVPDKIKX0DER': Marketplaces.US,
            'A2EUQ1WTGCTBG2': Marketplaces.CA,
            'A1AM78C64UM0Y8': Marketplaces.MX,
            'A1F83G8C2ARO7P': Marketplaces.UK,
            'A1PA6795UKMFR9': Marketplaces.DE,
            'A13V1IB3VIYBER': Marketplaces.FR,
            'APJ6JRA9NG5V4': Marketplaces.IT,
            'A1RKKUPIHCS9HS': Marketplaces.ES,
        }
        self.marketplace = marketplace_map.get(self.marketplace_id, Marketplaces.US)

    def get_shipped_orders(self, start_date: datetime, end_date: datetime = None) -> list:
        """
        Fetch all shipped orders within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range (defaults to now)

        Returns:
            List of order dictionaries with SKU, units, and monetary info
        """
        if end_date is None:
            end_date = datetime.utcnow()

        orders_api = Orders(credentials=self.credentials, marketplace=self.marketplace)

        try:
            # Get orders that have been shipped
            response = orders_api.get_orders(
                CreatedAfter=start_date.isoformat(),
                CreatedBefore=end_date.isoformat(),
                OrderStatuses=['Shipped'],
                MarketplaceIds=[self.marketplace_id]
            )

            orders = response.payload.get('Orders', [])
            logger.info(f"Found {len(orders)} shipped orders")

            # Get detailed info for each order
            detailed_orders = []
            for order in orders:
                order_id = order['AmazonOrderId']
                order_details = self._get_order_details(orders_api, order_id, order)
                if order_details:
                    detailed_orders.append(order_details)

            return detailed_orders

        except SellingApiException as e:
            logger.error(f"Amazon API error: {e}")
            raise

    def _get_order_details(self, orders_api: Orders, order_id: str, order: dict) -> dict:
        """
        Get detailed information for a single order including line items.

        Args:
            orders_api: Orders API instance
            order_id: Amazon order ID
            order: Basic order data

        Returns:
            Dictionary with complete order details
        """
        try:
            # Get order items (line items with SKU, quantity, price)
            items_response = orders_api.get_order_items(order_id)
            items = items_response.payload.get('OrderItems', [])

            # Parse order date
            purchase_date = order.get('PurchaseDate', '')
            if purchase_date:
                purchase_date = date_parser.parse(purchase_date)

            # Build line items with SKU, quantity, and price
            line_items = []
            total_amount = 0.0
            currency = 'USD'

            for item in items:
                sku = item.get('SellerSKU', '')
                quantity = int(item.get('QuantityShipped', 0))

                # Get item price
                item_price = item.get('ItemPrice', {})
                price_amount = float(item_price.get('Amount', 0))
                currency = item_price.get('CurrencyCode', 'USD')

                # Calculate unit price
                unit_price = price_amount / quantity if quantity > 0 else price_amount

                line_items.append({
                    'sku': sku,
                    'asin': item.get('ASIN', ''),
                    'title': item.get('Title', ''),
                    'quantity': quantity,
                    'unit_price': round(unit_price, 2),
                    'total_price': round(price_amount, 2),
                    'currency': currency
                })

                total_amount += price_amount

            return {
                'order_id': order_id,
                'purchase_date': purchase_date.isoformat() if purchase_date else '',
                'ship_date': order.get('LastUpdateDate', ''),
                'order_status': order.get('OrderStatus', ''),
                'fulfillment_channel': order.get('FulfillmentChannel', ''),
                'sales_channel': order.get('SalesChannel', 'Amazon.com'),
                'buyer_email': order.get('BuyerInfo', {}).get('BuyerEmail', ''),
                'shipping_address': self._parse_shipping_address(order),
                'line_items': line_items,
                'total_amount': round(total_amount, 2),
                'currency': currency
            }

        except SellingApiException as e:
            logger.error(f"Error getting order details for {order_id}: {e}")
            return None

    def _parse_shipping_address(self, order: dict) -> dict:
        """Extract shipping address from order."""
        address = order.get('ShippingAddress', {})
        return {
            'name': address.get('Name', ''),
            'address_line_1': address.get('AddressLine1', ''),
            'address_line_2': address.get('AddressLine2', ''),
            'city': address.get('City', ''),
            'state': address.get('StateOrRegion', ''),
            'postal_code': address.get('PostalCode', ''),
            'country': address.get('CountryCode', '')
        }

    def get_orders_by_date(self, target_date: datetime) -> list:
        """
        Get all shipped orders for a specific date.

        Args:
            target_date: The date to fetch orders for

        Returns:
            List of orders shipped on that date
        """
        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return self.get_shipped_orders(start, end)


# Example usage
if __name__ == '__main__':
    import json

    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)

    connector = AmazonConnector(config['amazon'])

    # Get orders from the last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    orders = connector.get_shipped_orders(yesterday)

    for order in orders:
        print(f"\nOrder: {order['order_id']}")
        print(f"Date: {order['purchase_date']}")
        for item in order['line_items']:
            print(f"  SKU: {item['sku']}, Qty: {item['quantity']}, Price: {item['total_price']} {item['currency']}")
