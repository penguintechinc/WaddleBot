"""
Admin web interface for managing service accounts and API keys
"""

import logging
from datetime import datetime, timedelta
from py4web import action, request, response, redirect, URL, HTTP
from py4web.utils.form import Form, FormStyleBulma
from py4web.utils.grid import Grid

from .. import auth, db
from ..services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Admin authentication decorator
def require_admin_auth(func):
    """Decorator to require admin authentication"""
    def wrapper(*args, **kwargs):
        if not auth.current_user:
            redirect(URL('admin/auth/login'))
        return func(*args, **kwargs)
    return wrapper

@action('admin')
@action.uses('admin/index.html', auth)
def admin_index():
    """Admin dashboard"""
    if not auth.current_user:
        redirect(URL('admin/auth/login'))
    
    # Get statistics
    total_accounts = db(db.service_accounts.id > 0).count()
    active_accounts = db(db.service_accounts.is_active == True).count()
    collector_accounts = db(
        (db.service_accounts.account_type == 'collector') & 
        (db.service_accounts.is_active == True)
    ).count()
    
    # Get recent API usage
    today = datetime.utcnow().date()
    api_requests_today = db(
        db.api_usage.timestamp >= today
    ).count()
    
    # Get top endpoints
    top_endpoints = db().select(
        db.api_usage.endpoint,
        db.api_usage.id.count(),
        groupby=db.api_usage.endpoint,
        orderby=~db.api_usage.id.count(),
        limitby=(0, 5)
    )
    
    return dict(
        user=auth.current_user,
        stats={
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'collector_accounts': collector_accounts,
            'api_requests_today': api_requests_today
        },
        top_endpoints=top_endpoints
    )

@action('admin/service-accounts')
@action.uses('admin/service_accounts.html', auth)
def service_accounts():
    """List and manage service accounts"""
    if not auth.current_user:
        redirect(URL('admin/auth/login'))
    
    # Configure grid
    grid = Grid(
        path=URL('admin/service-accounts'),
        query=db.service_accounts.id > 0,
        orderby=[db.service_accounts.created_at],
        columns=[
            db.service_accounts.account_name,
            db.service_accounts.account_type,
            db.service_accounts.platform,
            db.service_accounts.is_active,
            db.service_accounts.last_used,
            db.service_accounts.usage_count,
            db.service_accounts.created_at
        ],
        headings=[
            'Account Name',
            'Type',
            'Platform',
            'Active',
            'Last Used',
            'Usage Count',
            'Created'
        ],
        create=True,
        editable=True,
        deletable=True,
        details=True,
        formstyle=FormStyleBulma
    )
    
    return dict(grid=grid, user=auth.current_user)

@action('admin/service-accounts/create')
@action('admin/service-accounts/create', method='POST')
@action.uses('admin/create_service_account.html', auth)
def create_service_account():
    """Create new service account"""
    if not auth.current_user:
        redirect(URL('admin/auth/login'))
    
    form = Form(
        [
            {'name': 'account_name', 'type': 'string', 'label': 'Account Name', 'required': True},
            {'name': 'account_type', 'type': 'string', 'label': 'Account Type', 'required': True,
             'options': ['collector', 'interaction', 'webhook', 'admin']},
            {'name': 'platform', 'type': 'string', 'label': 'Platform (for collectors)', 'required': False},
            {'name': 'description', 'type': 'text', 'label': 'Description', 'required': False},
            {'name': 'rate_limit', 'type': 'integer', 'label': 'Rate Limit (requests/hour)', 'default': 1000}
        ],
        formstyle=FormStyleBulma
    )
    
    if form.accepted:
        try:
            # Create service account
            account_id, api_key = AuthService.create_service_account(
                account_name=form.vars['account_name'],
                account_type=form.vars['account_type'],
                platform=form.vars['platform'] or None,
                description=form.vars['description'],
                rate_limit=form.vars['rate_limit'] or 1000,
                created_by=auth.current_user.email
            )
            
            # Redirect to view page with API key
            redirect(URL('admin/service-accounts/view', account_id, vars={'api_key': api_key}))
            
        except Exception as e:
            logger.error(f"Error creating service account: {str(e)}")
            form.errors['account_name'] = str(e)
    
    return dict(form=form, user=auth.current_user)

@action('admin/service-accounts/view/<account_id:int>')
@action.uses('admin/view_service_account.html', auth)
def view_service_account(account_id):
    """View service account details"""
    if not auth.current_user:
        redirect(URL('admin/auth/login'))
    
    # Get service account
    account = db(db.service_accounts.id == account_id).select().first()
    if not account:
        raise HTTP(404, "Service account not found")
    
    # Get usage statistics
    usage_stats = AuthService.get_usage_stats(account_id, days=30)
    
    # Get recent API usage
    recent_usage = db(
        db.api_usage.service_account_id == account_id
    ).select(
        orderby=~db.api_usage.timestamp,
        limitby=(0, 20)
    )
    
    # Check for new API key in URL vars (from creation)
    new_api_key = request.query.get('api_key')
    
    return dict(
        account=account,
        usage_stats=usage_stats,
        recent_usage=recent_usage,
        new_api_key=new_api_key,
        user=auth.current_user
    )

@action('admin/service-accounts/regenerate/<account_id:int>')
@action('admin/service-accounts/regenerate/<account_id:int>', method='POST')
@action.uses('admin/regenerate_api_key.html', auth)
def regenerate_api_key(account_id):
    """Regenerate API key for service account"""
    if not auth.current_user:
        redirect(URL('admin/auth/login'))
    
    account = db(db.service_accounts.id == account_id).select().first()
    if not account:
        raise HTTP(404, "Service account not found")
    
    if request.method == 'POST':
        new_api_key = AuthService.regenerate_api_key(account_id)
        if new_api_key:
            redirect(URL('admin/service-accounts/view', account_id, vars={'api_key': new_api_key}))
        else:
            return dict(error="Failed to regenerate API key", account=account, user=auth.current_user)
    
    return dict(account=account, user=auth.current_user)

@action('admin/service-accounts/revoke/<account_id:int>')
@action('admin/service-accounts/revoke/<account_id:int>', method='POST')
@action.uses('admin/revoke_api_key.html', auth)
def revoke_api_key(account_id):
    """Revoke API key for service account"""
    if not auth.current_user:
        redirect(URL('admin/auth/login'))
    
    account = db(db.service_accounts.id == account_id).select().first()
    if not account:
        raise HTTP(404, "Service account not found")
    
    if request.method == 'POST':
        success = AuthService.revoke_api_key(account_id)
        if success:
            redirect(URL('admin/service-accounts/view', account_id))
        else:
            return dict(error="Failed to revoke API key", account=account, user=auth.current_user)
    
    return dict(account=account, user=auth.current_user)

@action('admin/api-usage')
@action.uses('admin/api_usage.html', auth)
def api_usage():
    """View API usage statistics"""
    if not auth.current_user:
        redirect(URL('admin/auth/login'))
    
    # Get filter parameters
    days = int(request.query.get('days', 7))
    account_id = request.query.get('account_id')
    
    # Get usage statistics
    usage_stats = AuthService.get_usage_stats(account_id, days)
    
    # Get accounts for filter dropdown
    accounts = db(db.service_accounts.is_active == True).select(
        orderby=db.service_accounts.account_name
    )
    
    # Get hourly usage for chart
    since_date = datetime.utcnow() - timedelta(days=days)
    hourly_usage = db(
        db.api_usage.timestamp > since_date
    ).select(
        db.api_usage.timestamp.date(),
        db.api_usage.timestamp.hour(),
        db.api_usage.id.count(),
        groupby=(db.api_usage.timestamp.date(), db.api_usage.timestamp.hour()),
        orderby=(db.api_usage.timestamp.date(), db.api_usage.timestamp.hour())
    )
    
    return dict(
        usage_stats=usage_stats,
        accounts=accounts,
        hourly_usage=hourly_usage,
        filters={'days': days, 'account_id': account_id},
        user=auth.current_user
    )

@action('admin/coordination')
@action.uses('admin/coordination.html', auth)
def coordination_dashboard():
    """View coordination system status"""
    if not auth.current_user:
        redirect(URL('admin/auth/login'))
    
    # Get coordination statistics
    from ..services.coordination_manager import get_coordination_manager
    coord_manager = get_coordination_manager()
    stats = coord_manager.get_stats()
    
    # Get recent entities
    entities = db(db.coordination.id > 0).select(
        orderby=~db.coordination.last_checkin,
        limitby=(0, 20)
    )
    
    # Get container distribution
    container_stats = db().select(
        db.coordination.claimed_by,
        db.coordination.platform,
        db.coordination.id.count(),
        groupby=(db.coordination.claimed_by, db.coordination.platform),
        having=(db.coordination.claimed_by != None)
    )
    
    return dict(
        stats=stats,
        entities=entities,
        container_stats=container_stats,
        user=auth.current_user
    )

# Authentication routes
@action('admin/auth/login')
@action('admin/auth/login', method='POST')
@action.uses('auth/login.html')
def login():
    """Admin login"""
    form = auth.form('login')
    if form.accepted:
        redirect(URL('admin'))
    return dict(form=form)

@action('admin/auth/logout')
@action.uses(auth)
def logout():
    """Admin logout"""
    auth.session.clear()
    redirect(URL('admin/auth/login'))

@action('admin/auth/register')
@action('admin/auth/register', method='POST')
@action.uses('auth/register.html')
def register():
    """Admin registration (requires approval)"""
    form = auth.form('register')
    if form.accepted:
        return dict(message="Registration submitted for approval")
    return dict(form=form)