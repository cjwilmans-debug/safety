#!/usr/bin/env python3
"""
Amazon Seller Central to Dynamics 365 Web Application

A web-based integration that uses OAuth login flows for both
Amazon and Dynamics 365 - no API keys needed, just click and authorize.
"""

import os
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler

from amazon_oauth import AmazonOAuth
from dynamics_oauth import DynamicsOAuth
from amazon_connector import AmazonConnector
from dynamics_connector import DynamicsConnector

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///integration.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Background scheduler for automated syncs
scheduler = BackgroundScheduler()


# =============================================================================
# Database Models
# =============================================================================

class Settings(db.Model):
    """Store application settings and tokens."""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class SyncedOrder(db.Model):
    """Track orders that have been synced."""
    id = db.Column(db.Integer, primary_key=True)
    amazon_order_id = db.Column(db.String(100), unique=True, nullable=False)
    dynamics_invoice_id = db.Column(db.String(100))
    order_date = db.Column(db.DateTime)
    total_amount = db.Column(db.Float)
    currency = db.Column(db.String(10))
    items_count = db.Column(db.Integer)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='success')
    error_message = db.Column(db.Text)


class SyncLog(db.Model):
    """Log sync operations."""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(100))
    orders_found = db.Column(db.Integer, default=0)
    orders_synced = db.Column(db.Integer, default=0)
    orders_skipped = db.Column(db.Integer, default=0)
    orders_failed = db.Column(db.Integer, default=0)
    message = db.Column(db.Text)


# =============================================================================
# Helper Functions
# =============================================================================

def get_setting(key, default=None):
    """Get a setting value from the database."""
    setting = Settings.query.filter_by(key=key).first()
    if setting:
        return setting.value
    return default


def set_setting(key, value):
    """Set a setting value in the database."""
    setting = Settings.query.filter_by(key=key).first()
    if setting:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    else:
        setting = Settings(key=key, value=value)
        db.session.add(setting)
    db.session.commit()


def is_amazon_connected():
    """Check if Amazon is connected."""
    return get_setting('amazon_refresh_token') is not None


def is_dynamics_connected():
    """Check if Dynamics 365 is connected."""
    return get_setting('dynamics_refresh_token') is not None


def requires_setup(f):
    """Decorator to ensure both services are connected."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_amazon_connected() or not is_dynamics_connected():
            flash('Please connect both Amazon and Dynamics 365 first.', 'warning')
            return redirect(url_for('setup'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Routes - Dashboard
# =============================================================================

@app.route('/')
def index():
    """Main dashboard."""
    amazon_connected = is_amazon_connected()
    dynamics_connected = is_dynamics_connected()

    # Get recent synced orders
    recent_orders = SyncedOrder.query.order_by(SyncedOrder.synced_at.desc()).limit(10).all()

    # Get sync statistics
    total_synced = SyncedOrder.query.filter_by(status='success').count()
    total_failed = SyncedOrder.query.filter_by(status='failed').count()

    # Get recent sync logs
    recent_logs = SyncLog.query.order_by(SyncLog.timestamp.desc()).limit(5).all()

    # Check if auto-sync is enabled
    auto_sync_enabled = get_setting('auto_sync_enabled', 'false') == 'true'

    return render_template('dashboard.html',
                         amazon_connected=amazon_connected,
                         dynamics_connected=dynamics_connected,
                         recent_orders=recent_orders,
                         total_synced=total_synced,
                         total_failed=total_failed,
                         recent_logs=recent_logs,
                         auto_sync_enabled=auto_sync_enabled)


@app.route('/setup')
def setup():
    """Setup page for connecting services."""
    return render_template('setup.html',
                         amazon_connected=is_amazon_connected(),
                         dynamics_connected=is_dynamics_connected(),
                         amazon_app_id=get_setting('amazon_app_id', ''),
                         dynamics_tenant_id=get_setting('dynamics_tenant_id', ''),
                         dynamics_client_id=get_setting('dynamics_client_id', ''))


# =============================================================================
# Routes - Amazon OAuth
# =============================================================================

@app.route('/setup/amazon', methods=['POST'])
def setup_amazon():
    """Save Amazon app credentials and initiate OAuth."""
    app_id = request.form.get('app_id')
    client_secret = request.form.get('client_secret')

    if not app_id or not client_secret:
        flash('Please provide both App ID and Client Secret.', 'error')
        return redirect(url_for('setup'))

    # Save credentials
    set_setting('amazon_app_id', app_id)
    set_setting('amazon_client_secret', client_secret)

    # Generate OAuth URL and redirect
    oauth = AmazonOAuth(app_id, client_secret)
    callback_url = url_for('amazon_callback', _external=True)
    auth_url, state = oauth.get_authorization_url(callback_url)

    session['amazon_oauth_state'] = state
    return redirect(auth_url)


@app.route('/callback/amazon')
def amazon_callback():
    """Handle Amazon OAuth callback."""
    error = request.args.get('error')
    if error:
        flash(f'Amazon authorization failed: {error}', 'error')
        return redirect(url_for('setup'))

    code = request.args.get('spapi_oauth_code')
    state = request.args.get('state')
    selling_partner_id = request.args.get('selling_partner_id')

    # Verify state
    if state != session.get('amazon_oauth_state'):
        flash('Invalid OAuth state. Please try again.', 'error')
        return redirect(url_for('setup'))

    # Exchange code for tokens
    app_id = get_setting('amazon_app_id')
    client_secret = get_setting('amazon_client_secret')
    oauth = AmazonOAuth(app_id, client_secret)

    callback_url = url_for('amazon_callback', _external=True)
    tokens = oauth.exchange_code_for_tokens(code, callback_url)

    if tokens:
        set_setting('amazon_refresh_token', tokens['refresh_token'])
        set_setting('amazon_selling_partner_id', selling_partner_id)
        flash('Successfully connected to Amazon Seller Central!', 'success')
    else:
        flash('Failed to get Amazon tokens. Please try again.', 'error')

    return redirect(url_for('setup'))


@app.route('/disconnect/amazon', methods=['POST'])
def disconnect_amazon():
    """Disconnect Amazon account."""
    Settings.query.filter(Settings.key.like('amazon_%')).delete()
    db.session.commit()
    flash('Amazon account disconnected.', 'info')
    return redirect(url_for('setup'))


# =============================================================================
# Routes - Dynamics 365 OAuth
# =============================================================================

@app.route('/setup/dynamics', methods=['POST'])
def setup_dynamics():
    """Save Dynamics 365 app credentials and initiate OAuth."""
    tenant_id = request.form.get('tenant_id')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    environment = request.form.get('environment', 'Production')

    if not all([tenant_id, client_id, client_secret]):
        flash('Please provide Tenant ID, Client ID, and Client Secret.', 'error')
        return redirect(url_for('setup'))

    # Save credentials
    set_setting('dynamics_tenant_id', tenant_id)
    set_setting('dynamics_client_id', client_id)
    set_setting('dynamics_client_secret', client_secret)
    set_setting('dynamics_environment', environment)

    # Generate OAuth URL and redirect
    oauth = DynamicsOAuth(tenant_id, client_id, client_secret)
    callback_url = url_for('dynamics_callback', _external=True)
    auth_url, state = oauth.get_authorization_url(callback_url)

    session['dynamics_oauth_state'] = state
    return redirect(auth_url)


@app.route('/callback/dynamics')
def dynamics_callback():
    """Handle Dynamics 365 OAuth callback."""
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', '')
        flash(f'Dynamics 365 authorization failed: {error_desc}', 'error')
        return redirect(url_for('setup'))

    code = request.args.get('code')
    state = request.args.get('state')

    # Verify state
    if state != session.get('dynamics_oauth_state'):
        flash('Invalid OAuth state. Please try again.', 'error')
        return redirect(url_for('setup'))

    # Exchange code for tokens
    tenant_id = get_setting('dynamics_tenant_id')
    client_id = get_setting('dynamics_client_id')
    client_secret = get_setting('dynamics_client_secret')

    oauth = DynamicsOAuth(tenant_id, client_id, client_secret)
    callback_url = url_for('dynamics_callback', _external=True)
    tokens = oauth.exchange_code_for_tokens(code, callback_url)

    if tokens:
        set_setting('dynamics_refresh_token', tokens['refresh_token'])
        set_setting('dynamics_access_token', tokens['access_token'])

        # Fetch and save available companies
        oauth.access_token = tokens['access_token']
        companies = oauth.get_companies(get_setting('dynamics_environment'))
        if companies:
            set_setting('dynamics_companies', json.dumps(companies))
            if len(companies) == 1:
                set_setting('dynamics_company_id', companies[0]['id'])

        flash('Successfully connected to Dynamics 365!', 'success')
    else:
        flash('Failed to get Dynamics 365 tokens. Please try again.', 'error')

    return redirect(url_for('setup'))


@app.route('/setup/dynamics/company', methods=['POST'])
def select_dynamics_company():
    """Select which Dynamics 365 company to use."""
    company_id = request.form.get('company_id')
    if company_id:
        set_setting('dynamics_company_id', company_id)
        flash('Company selected successfully.', 'success')
    return redirect(url_for('setup'))


@app.route('/disconnect/dynamics', methods=['POST'])
def disconnect_dynamics():
    """Disconnect Dynamics 365 account."""
    Settings.query.filter(Settings.key.like('dynamics_%')).delete()
    db.session.commit()
    flash('Dynamics 365 account disconnected.', 'info')
    return redirect(url_for('setup'))


# =============================================================================
# Routes - Sync Operations
# =============================================================================

@app.route('/sync', methods=['POST'])
@requires_setup
def sync_orders():
    """Manually trigger order sync."""
    days_back = int(request.form.get('days_back', 1))
    create_invoice = request.form.get('document_type', 'invoice') == 'invoice'

    result = run_sync(days_back, create_invoice)

    if result['success']:
        flash(f"Sync complete! Synced {result['synced']} orders, skipped {result['skipped']}, failed {result['failed']}.", 'success')
    else:
        flash(f"Sync failed: {result['error']}", 'error')

    return redirect(url_for('index'))


@app.route('/api/sync', methods=['POST'])
@requires_setup
def api_sync_orders():
    """API endpoint for sync (for AJAX calls)."""
    data = request.get_json() or {}
    days_back = data.get('days_back', 1)
    create_invoice = data.get('document_type', 'invoice') == 'invoice'

    result = run_sync(days_back, create_invoice)
    return jsonify(result)


def run_sync(days_back=1, create_invoice=True):
    """Execute the sync operation."""
    try:
        # Get credentials from database
        amazon_config = {
            'refresh_token': get_setting('amazon_refresh_token'),
            'lwa_app_id': get_setting('amazon_app_id'),
            'lwa_client_secret': get_setting('amazon_client_secret'),
            'marketplace_id': get_setting('amazon_marketplace_id', 'ATVPDKIKX0DER')
        }

        dynamics_config = {
            'tenant_id': get_setting('dynamics_tenant_id'),
            'client_id': get_setting('dynamics_client_id'),
            'client_secret': get_setting('dynamics_client_secret'),
            'environment': get_setting('dynamics_environment', 'Production'),
            'company_id': get_setting('dynamics_company_id')
        }

        # Initialize connectors
        amazon = AmazonConnector(amazon_config)
        dynamics = DynamicsConnector(dynamics_config)

        # Fetch orders
        start_date = datetime.utcnow() - timedelta(days=days_back)
        orders = amazon.get_shipped_orders(start_date)

        synced = 0
        skipped = 0
        failed = 0

        for order in orders:
            order_id = order['order_id']

            # Check if already synced
            existing = SyncedOrder.query.filter_by(amazon_order_id=order_id).first()
            if existing:
                skipped += 1
                continue

            # Check if exists in Dynamics
            if dynamics.check_order_exists(order_id):
                # Record it as synced
                synced_order = SyncedOrder(
                    amazon_order_id=order_id,
                    order_date=datetime.fromisoformat(order['purchase_date'].replace('Z', '+00:00')) if order.get('purchase_date') else None,
                    total_amount=order.get('total_amount', 0),
                    currency=order.get('currency', 'USD'),
                    items_count=len(order.get('line_items', [])),
                    status='skipped'
                )
                db.session.add(synced_order)
                skipped += 1
                continue

            try:
                # Create in Dynamics
                if create_invoice:
                    result = dynamics.create_sales_invoice(order)
                else:
                    result = dynamics.create_sales_order(order)

                # Record success
                synced_order = SyncedOrder(
                    amazon_order_id=order_id,
                    dynamics_invoice_id=result.get('id', ''),
                    order_date=datetime.fromisoformat(order['purchase_date'].replace('Z', '+00:00')) if order.get('purchase_date') else None,
                    total_amount=order.get('total_amount', 0),
                    currency=order.get('currency', 'USD'),
                    items_count=len(order.get('line_items', [])),
                    status='success'
                )
                db.session.add(synced_order)
                synced += 1

            except Exception as e:
                # Record failure
                synced_order = SyncedOrder(
                    amazon_order_id=order_id,
                    order_date=datetime.fromisoformat(order['purchase_date'].replace('Z', '+00:00')) if order.get('purchase_date') else None,
                    total_amount=order.get('total_amount', 0),
                    currency=order.get('currency', 'USD'),
                    items_count=len(order.get('line_items', [])),
                    status='failed',
                    error_message=str(e)
                )
                db.session.add(synced_order)
                failed += 1

        # Log the sync
        sync_log = SyncLog(
            action='manual_sync',
            orders_found=len(orders),
            orders_synced=synced,
            orders_skipped=skipped,
            orders_failed=failed,
            message=f'Synced {synced} orders from last {days_back} days'
        )
        db.session.add(sync_log)
        db.session.commit()

        return {
            'success': True,
            'total': len(orders),
            'synced': synced,
            'skipped': skipped,
            'failed': failed
        }

    except Exception as e:
        # Log the error
        sync_log = SyncLog(
            action='manual_sync',
            message=f'Error: {str(e)}'
        )
        db.session.add(sync_log)
        db.session.commit()

        return {
            'success': False,
            'error': str(e)
        }


# =============================================================================
# Routes - Auto Sync Settings
# =============================================================================

@app.route('/settings/auto-sync', methods=['POST'])
@requires_setup
def toggle_auto_sync():
    """Enable or disable automatic syncing."""
    enabled = request.form.get('enabled') == 'true'
    interval = int(request.form.get('interval', 60))

    set_setting('auto_sync_enabled', 'true' if enabled else 'false')
    set_setting('auto_sync_interval', str(interval))

    # Update scheduler
    scheduler.remove_all_jobs()
    if enabled:
        scheduler.add_job(
            func=lambda: run_sync(days_back=1, create_invoice=True),
            trigger='interval',
            minutes=interval,
            id='auto_sync'
        )
        flash(f'Auto-sync enabled. Running every {interval} minutes.', 'success')
    else:
        flash('Auto-sync disabled.', 'info')

    return redirect(url_for('index'))


# =============================================================================
# Routes - Order History
# =============================================================================

@app.route('/orders')
def orders():
    """View synced order history."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = SyncedOrder.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(SyncedOrder.synced_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('orders.html', orders=orders, status_filter=status_filter)


@app.route('/logs')
def logs():
    """View sync logs."""
    page = request.args.get('page', 1, type=int)
    logs = SyncLog.query.order_by(SyncLog.timestamp.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('logs.html', logs=logs)


# =============================================================================
# Routes - API Endpoints
# =============================================================================

@app.route('/api/status')
def api_status():
    """Get current connection status."""
    return jsonify({
        'amazon_connected': is_amazon_connected(),
        'dynamics_connected': is_dynamics_connected(),
        'auto_sync_enabled': get_setting('auto_sync_enabled', 'false') == 'true'
    })


@app.route('/api/orders/recent')
def api_recent_orders():
    """Get recent synced orders."""
    orders = SyncedOrder.query.order_by(SyncedOrder.synced_at.desc()).limit(10).all()
    return jsonify([{
        'amazon_order_id': o.amazon_order_id,
        'total_amount': o.total_amount,
        'currency': o.currency,
        'items_count': o.items_count,
        'synced_at': o.synced_at.isoformat() if o.synced_at else None,
        'status': o.status
    } for o in orders])


# =============================================================================
# Initialize App
# =============================================================================

def init_app():
    """Initialize the application."""
    with app.app_context():
        db.create_all()

        # Start scheduler if auto-sync was enabled
        if get_setting('auto_sync_enabled', 'false') == 'true':
            interval = int(get_setting('auto_sync_interval', 60))
            scheduler.add_job(
                func=lambda: run_sync(days_back=1, create_invoice=True),
                trigger='interval',
                minutes=interval,
                id='auto_sync'
            )

    scheduler.start()


if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
