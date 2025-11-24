#!/usr/bin/env python3
"""
Amazon Seller Central to Dynamics 365 Integration

This script automatically syncs shipped orders from Amazon Seller Central
to Microsoft Dynamics 365 Business Central, creating sales invoices.

Usage:
    python main.py                  # Run once
    python main.py --schedule       # Run continuously on schedule
    python main.py --date 2024-01-15  # Sync orders for specific date
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import schedule
import time

from amazon_connector import AmazonConnector
from dynamics_connector import DynamicsConnector

# Configure logging
def setup_logging(log_file: str = None):
    """Configure logging to console and optionally file."""
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

logger = logging.getLogger(__name__)


class AmazonDynamicsIntegration:
    """Main integration class that syncs Amazon orders to Dynamics 365."""

    def __init__(self, config_path: str = 'config.json'):
        """
        Initialize the integration with configuration.

        Args:
            config_path: Path to the configuration JSON file
        """
        self.config = self._load_config(config_path)
        self.amazon = AmazonConnector(self.config['amazon'])
        self.dynamics = DynamicsConnector(self.config['dynamics365'])
        self.settings = self.config.get('settings', {})

        # Track processed orders to avoid duplicates
        self.processed_orders_file = 'processed_orders.json'
        self.processed_orders = self._load_processed_orders()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                "Please copy config_template.json to config.json and fill in your credentials."
            )

        with open(path, 'r') as f:
            return json.load(f)

    def _load_processed_orders(self) -> set:
        """Load list of already processed order IDs."""
        if os.path.exists(self.processed_orders_file):
            with open(self.processed_orders_file, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_processed_order(self, order_id: str):
        """Save an order ID as processed."""
        self.processed_orders.add(order_id)
        with open(self.processed_orders_file, 'w') as f:
            json.dump(list(self.processed_orders), f)

    def sync_orders(self, start_date: datetime = None, end_date: datetime = None,
                    create_invoice: bool = True) -> dict:
        """
        Sync shipped orders from Amazon to Dynamics 365.

        Args:
            start_date: Start of date range (defaults to days_to_look_back from config)
            end_date: End of date range (defaults to now)
            create_invoice: If True, create invoices; if False, create sales orders

        Returns:
            Dictionary with sync results
        """
        if start_date is None:
            days_back = self.settings.get('days_to_look_back', 1)
            start_date = datetime.utcnow() - timedelta(days=days_back)

        if end_date is None:
            end_date = datetime.utcnow()

        logger.info(f"Starting sync for orders from {start_date} to {end_date}")

        results = {
            'total_orders': 0,
            'synced_orders': 0,
            'skipped_orders': 0,
            'failed_orders': 0,
            'errors': []
        }

        try:
            # Fetch shipped orders from Amazon
            orders = self.amazon.get_shipped_orders(start_date, end_date)
            results['total_orders'] = len(orders)
            logger.info(f"Found {len(orders)} shipped orders from Amazon")

            for order in orders:
                order_id = order['order_id']

                # Skip if already processed
                if order_id in self.processed_orders:
                    logger.info(f"Skipping already processed order: {order_id}")
                    results['skipped_orders'] += 1
                    continue

                # Check if order exists in Dynamics
                if self.dynamics.check_order_exists(order_id):
                    logger.info(f"Order {order_id} already exists in Dynamics 365")
                    self._save_processed_order(order_id)
                    results['skipped_orders'] += 1
                    continue

                try:
                    # Create invoice or sales order in Dynamics
                    if create_invoice:
                        self.dynamics.create_sales_invoice(order)
                    else:
                        self.dynamics.create_sales_order(order)

                    self._save_processed_order(order_id)
                    results['synced_orders'] += 1
                    logger.info(f"Successfully synced order: {order_id}")

                    # Log order details
                    self._log_order_summary(order)

                except Exception as e:
                    results['failed_orders'] += 1
                    error_msg = f"Failed to sync order {order_id}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)

        except Exception as e:
            error_msg = f"Error fetching orders from Amazon: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(error_msg)

        self._log_sync_summary(results)
        return results

    def _log_order_summary(self, order: dict):
        """Log a summary of an order."""
        logger.info(f"  Order ID: {order['order_id']}")
        logger.info(f"  Date: {order['purchase_date']}")
        logger.info(f"  Total: {order['total_amount']} {order['currency']}")
        logger.info(f"  Items:")
        for item in order['line_items']:
            logger.info(f"    - SKU: {item['sku']}, Qty: {item['quantity']}, "
                       f"Price: {item['total_price']} {item['currency']}")

    def _log_sync_summary(self, results: dict):
        """Log a summary of the sync operation."""
        logger.info("=" * 50)
        logger.info("SYNC SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total orders found: {results['total_orders']}")
        logger.info(f"Orders synced: {results['synced_orders']}")
        logger.info(f"Orders skipped: {results['skipped_orders']}")
        logger.info(f"Orders failed: {results['failed_orders']}")
        if results['errors']:
            logger.info("Errors:")
            for error in results['errors']:
                logger.info(f"  - {error}")
        logger.info("=" * 50)

    def sync_specific_date(self, target_date: datetime, create_invoice: bool = True) -> dict:
        """
        Sync orders for a specific date.

        Args:
            target_date: The date to sync orders for
            create_invoice: If True, create invoices; if False, create sales orders

        Returns:
            Dictionary with sync results
        """
        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return self.sync_orders(start, end, create_invoice)

    def run_scheduled(self):
        """Run the sync on a schedule."""
        interval = self.settings.get('sync_interval_minutes', 60)
        logger.info(f"Starting scheduled sync every {interval} minutes")

        # Run immediately
        self.sync_orders()

        # Schedule future runs
        schedule.every(interval).minutes.do(self.sync_orders)

        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sync Amazon Seller Central orders to Dynamics 365'
    )
    parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    parser.add_argument(
        '--schedule', '-s',
        action='store_true',
        help='Run continuously on schedule'
    )
    parser.add_argument(
        '--date', '-d',
        help='Sync orders for a specific date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--days-back', '-b',
        type=int,
        help='Number of days to look back (overrides config)'
    )
    parser.add_argument(
        '--sales-order',
        action='store_true',
        help='Create sales orders instead of invoices'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch orders but do not create anything in Dynamics'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    try:
        integration = AmazonDynamicsIntegration(args.config)

        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made to Dynamics 365")
            days_back = args.days_back or integration.settings.get('days_to_look_back', 1)
            start_date = datetime.utcnow() - timedelta(days=days_back)

            orders = integration.amazon.get_shipped_orders(start_date)
            logger.info(f"\nFound {len(orders)} orders:")
            for order in orders:
                integration._log_order_summary(order)
            return

        if args.schedule:
            integration.run_scheduled()
        elif args.date:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
            integration.sync_specific_date(target_date, create_invoice=not args.sales_order)
        else:
            if args.days_back:
                start_date = datetime.utcnow() - timedelta(days=args.days_back)
                integration.sync_orders(start_date, create_invoice=not args.sales_order)
            else:
                integration.sync_orders(create_invoice=not args.sales_order)

    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
