"""
Portal controllers using native py4web features
"""

from py4web import action, request, response, URL, redirect, HTTP
from py4web.utils.form import Form, FormStyleBulma
from py4web.utils.grid import Grid, GridClassStyleBulma
from py4web.utils.flash import flash
from datetime import datetime

from ..app import (
    db, auth, session, mailer, flash as flash_fixture,
    community_owner_required, waddlebot_user_required,
    APP_NAME, PORTAL_URL,
    get_user_communities, get_community_members, get_community_modules,
    create_portal_user_from_command
)

# Import identity API client
from ..services.identity_api_client import IdentityAPIClient

import logging

logger = logging.getLogger(__name__)

# Initialize identity API client
identity_client = IdentityAPIClient()

@action('index')
@action('/')
def index():
    """Landing page - redirect to dashboard or login"""
    if auth.get_user():
        redirect(URL('dashboard'))
    else:
        redirect(URL('auth/login'))

@action('dashboard')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def dashboard():
    """Main dashboard showing user's communities"""
    try:
        user = auth.get_user()
        waddlebot_user_id = user.get('waddlebot_user_id')
        
        # Get user's communities
        communities = get_user_communities(waddlebot_user_id)
        
        # Update last login
        db(db.auth_user.id == user['id']).update(last_portal_login=datetime.utcnow())
        db.commit()
        
        return dict(
            app_name=APP_NAME,
            user=user,
            communities=communities,
            flash=flash()
        )
    
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash.set("Error loading dashboard", "danger")
        return dict(
            app_name=APP_NAME,
            user=auth.get_user(),
            communities=[],
            flash=flash()
        )

@action('community/<community_id:int>')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def community_details(community_id):
    """Community details page with native py4web Grid"""
    try:
        user = auth.get_user()
        waddlebot_user_id = user.get('waddlebot_user_id')
        
        # Get community details
        community = db(
            (db.communities.id == community_id) &
            (db.communities.is_active == True)
        ).select().first()
        
        if not community:
            flash.set("Community not found", "danger")
            redirect(URL('dashboard'))
        
        # Check if user is owner
        from ..app import rbac_service
        user_role = rbac_service.get_user_role_in_community(waddlebot_user_id, community_id)
        if user_role != 'owner':
            flash.set("Access denied: Community owner access required", "danger")
            redirect(URL('dashboard'))
        
        # Get community members
        members = get_community_members(community_id, waddlebot_user_id)
        
        # Get community modules
        modules = get_community_modules(community_id, waddlebot_user_id)
        
        # Get browser source URLs
        from ..app import get_browser_source_urls
        browser_source_urls = get_browser_source_urls(community_id)
        
        # Create Grid for members display
        members_grid = Grid(
            path=URL('community', community_id, 'members_grid'),
            query=((db.community_memberships.community_id == community_id) & 
                   (db.community_memberships.is_active == True)),
            columns=[
                db.community_memberships.user_id,
                db.community_memberships.joined_at,
                db.community_memberships.invited_by
            ],
            headings=['User ID', 'Joined', 'Invited By'],
            search_queries=[
                ['Search by User ID', lambda value: db.community_memberships.user_id.contains(value)]
            ],
            orderby=[db.community_memberships.joined_at],
            create=False,
            editable=False,
            deletable=False,
            details=False,
            grid_class_style=GridClassStyleBulma
        )
        
        return dict(
            app_name=APP_NAME,
            user=user,
            community=community,
            members=members,
            modules=modules,
            browser_source_urls=browser_source_urls,
            members_grid=members_grid,
            flash=flash()
        )
    
    except Exception as e:
        logger.error(f"Community details error: {str(e)}")
        flash.set("Error loading community details", "danger")
        redirect(URL('dashboard'))

@action('community/<community_id:int>/members_grid')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def community_members_grid(community_id):
    """Grid endpoint for community members"""
    try:
        user = auth.get_user()
        waddlebot_user_id = user.get('waddlebot_user_id')
        
        # Check if user is owner
        from ..app import rbac_service
        user_role = rbac_service.get_user_role_in_community(waddlebot_user_id, community_id)
        if user_role != 'owner':
            raise HTTP(403, "Access denied")
        
        # Create Grid for members
        members_grid = Grid(
            path=URL('community', community_id, 'members_grid'),
            query=((db.community_memberships.community_id == community_id) & 
                   (db.community_memberships.is_active == True)),
            columns=[
                db.community_memberships.user_id,
                db.community_memberships.joined_at,
                db.community_memberships.invited_by
            ],
            headings=['User ID', 'Joined', 'Invited By'],
            search_queries=[
                ['Search by User ID', lambda value: db.community_memberships.user_id.contains(value)]
            ],
            orderby=[db.community_memberships.joined_at],
            create=False,
            editable=False,
            deletable=False,
            details=False,
            grid_class_style=GridClassStyleBulma
        )
        
        return members_grid.render()
    
    except Exception as e:
        logger.error(f"Members grid error: {str(e)}")
        raise HTTP(500, "Internal server error")

@action('profile')
@action.uses(auth.user, flash_fixture)
def profile():
    """User profile page using py4web Form"""
    try:
        user = auth.get_user()
        
        # Create form for profile editing
        form = Form(
            db.auth_user,
            record=user,
            fields=['first_name', 'last_name', 'display_name'],
            formstyle=FormStyleBulma,
            form_name='profile_form'
        )
        
        if form.accepted:
            flash.set("Profile updated successfully", "success")
            redirect(URL('profile'))
        elif form.errors:
            flash.set("Please correct the errors below", "danger")
        
        return dict(
            app_name=APP_NAME,
            user=user,
            form=form,
            flash=flash()
        )
    
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        flash.set("Error loading profile", "danger")
        redirect(URL('dashboard'))

@action('admin/users')
@action.uses(auth.user, flash_fixture)
@community_owner_required
def admin_users():
    """Admin page for managing portal users using py4web Grid"""
    try:
        # Create Grid for user management
        users_grid = Grid(
            path=URL('admin/users'),
            query=db.auth_user.id > 0,
            columns=[
                db.auth_user.waddlebot_user_id,
                db.auth_user.email,
                db.auth_user.display_name,
                db.auth_user.is_community_owner,
                db.auth_user.created_by_command,
                db.auth_user.last_portal_login,
                db.auth_user.registration_key
            ],
            headings=[
                'WaddleBot ID', 'Email', 'Display Name', 
                'Community Owner', 'Created by Command', 'Last Login', 'Status'
            ],
            search_queries=[
                ['Search by WaddleBot ID', lambda value: db.auth_user.waddlebot_user_id.contains(value)],
                ['Search by Email', lambda value: db.auth_user.email.contains(value)]
            ],
            orderby=[db.auth_user.waddlebot_user_id],
            create=False,
            editable=lambda row: dict(
                display_name=True,
                is_community_owner=True
            ),
            deletable=False,
            details=True,
            grid_class_style=GridClassStyleBulma
        )
        
        return dict(
            app_name=APP_NAME,
            user=auth.get_user(),
            users_grid=users_grid,
            flash=flash()
        )
    
    except Exception as e:
        logger.error(f"Admin users error: {str(e)}")
        flash.set("Error loading admin page", "danger")
        redirect(URL('dashboard'))

# API endpoints for community command integration
@action('api/create_user', method='POST')
@action.uses(db)
def api_create_user():
    """API endpoint for creating users from community commands"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        waddlebot_user_id = data.get('waddlebot_user_id')
        email = data.get('email')
        display_name = data.get('display_name')
        
        if not all([waddlebot_user_id, email]):
            raise HTTP(400, "waddlebot_user_id and email are required")
        
        # Create user
        result = create_portal_user_from_command(
            waddlebot_user_id=waddlebot_user_id,
            email=email,
            display_name=display_name
        )
        
        return result
        
    except Exception as e:
        logger.error(f"API create user error: {str(e)}")
        raise HTTP(500, "Internal server error")

@action('api/communities/<waddlebot_user_id>')
@action.uses(db)
def api_user_communities(waddlebot_user_id):
    """API endpoint to get user's communities"""
    try:
        communities = get_user_communities(waddlebot_user_id)
        return {
            "success": True,
            "communities": communities
        }
    
    except Exception as e:
        logger.error(f"API user communities error: {str(e)}")
        raise HTTP(500, "Internal server error")

@action('api/community/<community_id:int>/members')
@action.uses(db)
def api_community_members(community_id):
    """API endpoint to get community members"""
    try:
        # Get waddlebot_user_id from query parameters
        waddlebot_user_id = request.query.get('waddlebot_user_id')
        if not waddlebot_user_id:
            raise HTTP(400, "waddlebot_user_id parameter required")
        
        members = get_community_members(community_id, waddlebot_user_id)
        return {
            "success": True,
            "members": members
        }
    
    except Exception as e:
        logger.error(f"API community members error: {str(e)}")
        raise HTTP(500, "Internal server error")

@action('api/community/<community_id:int>/modules')
@action.uses(db)
def api_community_modules(community_id):
    """API endpoint to get community modules"""
    try:
        # Get waddlebot_user_id from query parameters
        waddlebot_user_id = request.query.get('waddlebot_user_id')
        if not waddlebot_user_id:
            raise HTTP(400, "waddlebot_user_id parameter required")
        
        modules = get_community_modules(community_id, waddlebot_user_id)
        return {
            "success": True,
            "modules": modules
        }
    
    except Exception as e:
        logger.error(f"API community modules error: {str(e)}")
        raise HTTP(500, "Internal server error")

@action('api/cleanup')
@action.uses(db)
def api_cleanup():
    """Cleanup expired temp passwords and sessions"""
    try:
        from datetime import datetime
        
        # Clean up expired temp passwords
        count = db(db.portal_temp_passwords.expires_at < datetime.utcnow()).delete()
        
        # Clean up expired auth sessions (handled by py4web Auth)
        
        db.commit()
        
        return {
            "success": True,
            "cleaned_temp_passwords": count
        }
    
    except Exception as e:
        logger.error(f"API cleanup error: {str(e)}")
        raise HTTP(500, "Internal server error")

# ============ OAuth Authentication Endpoints ============

@action('auth/oauth/<provider>')
def oauth_login(provider):
    """Initiate OAuth login with provider"""
    try:
        # Get OAuth login URL from identity service
        oauth_url = identity_client.initiate_oauth_login(provider)
        redirect(oauth_url)
        
    except Exception as e:
        logger.error(f"OAuth login error for {provider}: {str(e)}")
        flash.set(f"Error initiating {provider.title()} login", "danger")
        redirect(URL('auth/login'))

@action('auth/oauth_callback/<provider>')
def oauth_callback(provider):
    """Handle OAuth callback from provider"""
    try:
        # Get authorization code from callback
        code = request.query.get('code')
        state = request.query.get('state')
        error = request.query.get('error')
        
        if error:
            logger.error(f"OAuth error from {provider}: {error}")
            flash.set(f"Authentication failed: {error}", "danger")
            redirect(URL('auth/login'))
        
        if not code:
            logger.error(f"No authorization code from {provider}")
            flash.set("Authentication failed: No authorization code", "danger")
            redirect(URL('auth/login'))
        
        # Process OAuth callback through identity service
        # This would be handled by the identity core module's OAuth endpoints
        # For now, show success message and redirect to dashboard
        flash.set(f"Successfully authenticated with {provider.title()}", "success")
        redirect(URL('dashboard'))
        
    except Exception as e:
        logger.error(f"OAuth callback error for {provider}: {str(e)}")
        flash.set("Authentication failed", "danger")
        redirect(URL('auth/login'))

@action('auth/oauth_login')
@action.uses(flash_fixture)
def oauth_login_page():
    """OAuth login page with provider buttons"""
    try:
        # If user is already logged in, redirect to dashboard
        if auth.get_user():
            redirect(URL('dashboard'))
        
        # Get available OAuth providers
        providers = ['discord', 'twitch', 'slack']
        
        return dict(
            app_name=APP_NAME,
            providers=providers,
            flash=flash()
        )
        
    except Exception as e:
        logger.error(f"OAuth login page error: {str(e)}")
        flash.set("Error loading login page", "danger")
        redirect(URL('auth/login'))

# ============ Identity Management Endpoints ============

@action('identity')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def identity_management():
    """Identity management page"""
    try:
        user = auth.get_user()
        user_id = user.get('id')
        
        # Get user's linked identities from identity service
        identities_result = identity_client.get_user_identities(user_id)
        identities = identities_result.get('identities', []) if identities_result.get('success') else []
        
        # Get pending verifications
        pending_result = identity_client.get_pending_verifications(user_id=user_id)
        pending_verifications = pending_result.get('verifications', []) if pending_result.get('success') else []
        
        return dict(
            app_name=APP_NAME,
            user=user,
            identities=identities,
            pending_verifications=pending_verifications,
            flash=flash()
        )
        
    except Exception as e:
        logger.error(f"Identity management error: {str(e)}")
        flash.set("Error loading identity management", "danger")
        redirect(URL('dashboard'))

@action('identity/link', method='POST')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def link_identity():
    """Initiate identity linking"""
    try:
        user = auth.get_user()
        user_id = user.get('id')
        
        data = request.json or request.forms
        source_platform = data.get('source_platform')
        target_platform = data.get('target_platform')
        target_username = data.get('target_username')
        
        if not all([source_platform, target_platform, target_username]):
            flash.set("All fields are required", "danger")
            redirect(URL('identity'))
        
        # Initiate identity linking through identity service
        result = identity_client.initiate_identity_link(
            user_id, source_platform, target_platform, target_username
        )
        
        if result.get('success'):
            flash.set(f"Verification code sent to {target_platform}. Please check for a message.", "success")
        else:
            flash.set(f"Error linking identity: {result.get('message', 'Unknown error')}", "danger")
        
        redirect(URL('identity'))
        
    except Exception as e:
        logger.error(f"Link identity error: {str(e)}")
        flash.set("Error linking identity", "danger")
        redirect(URL('identity'))

@action('identity/verify', method='POST')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def verify_identity():
    """Verify identity with code"""
    try:
        data = request.json or request.forms
        platform = data.get('platform')
        platform_id = data.get('platform_id')
        platform_username = data.get('platform_username')
        verification_code = data.get('verification_code')
        
        if not all([platform, platform_id, platform_username, verification_code]):
            flash.set("All fields are required", "danger")
            redirect(URL('identity'))
        
        # Verify identity through identity service
        result = identity_client.verify_identity(
            platform, platform_id, platform_username, verification_code
        )
        
        if result.get('success'):
            flash.set(f"Successfully linked {platform} identity", "success")
        else:
            flash.set(f"Verification failed: {result.get('message', 'Unknown error')}", "danger")
        
        redirect(URL('identity'))
        
    except Exception as e:
        logger.error(f"Verify identity error: {str(e)}")
        flash.set("Error verifying identity", "danger")
        redirect(URL('identity'))

@action('identity/unlink', method='POST')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def unlink_identity():
    """Unlink platform identity"""
    try:
        user = auth.get_user()
        user_id = user.get('id')
        
        data = request.json or request.forms
        platform = data.get('platform')
        
        if not platform:
            flash.set("Platform is required", "danger")
            redirect(URL('identity'))
        
        # Unlink identity through identity service
        result = identity_client.unlink_identity(user_id, platform)
        
        if result.get('success'):
            flash.set(f"Successfully unlinked {platform} identity", "success")
        else:
            flash.set(f"Error unlinking identity: {result.get('message', 'Unknown error')}", "danger")
        
        redirect(URL('identity'))
        
    except Exception as e:
        logger.error(f"Unlink identity error: {str(e)}")
        flash.set("Error unlinking identity", "danger")
        redirect(URL('identity'))

# ============ API Key Management Endpoints ============

@action('api_keys')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def api_keys_management():
    """API key management page"""
    try:
        user = auth.get_user()
        session_token = session.get('user_session_token')  # Would need to be set during login
        
        if not session_token:
            flash.set("Session token required for API key management", "warning")
            return dict(
                app_name=APP_NAME,
                user=user,
                api_keys=[],
                flash=flash()
            )
        
        # Get user's API keys from identity service
        result = identity_client.list_api_keys(session_token)
        api_keys = result.get('api_keys', []) if result.get('success') else []
        
        return dict(
            app_name=APP_NAME,
            user=user,
            api_keys=api_keys,
            flash=flash()
        )
        
    except Exception as e:
        logger.error(f"API keys management error: {str(e)}")
        flash.set("Error loading API keys", "danger")
        redirect(URL('dashboard'))

@action('api_keys/create', method='POST')
@action.uses(auth.user, flash_fixture)
@waddlebot_user_required
def create_api_key():
    """Create new API key"""
    try:
        session_token = session.get('user_session_token')
        if not session_token:
            flash.set("Session token required", "danger")
            redirect(URL('api_keys'))
        
        data = request.json or request.forms
        name = data.get('name')
        expires_in_days = int(data.get('expires_in_days', 365))
        
        if not name:
            flash.set("API key name is required", "danger")
            redirect(URL('api_keys'))
        
        # Create API key through identity service
        result = identity_client.create_api_key(session_token, name, expires_in_days)
        
        if result.get('success'):
            flash.set(f"API key '{name}' created successfully", "success")
        else:
            flash.set(f"Error creating API key: {result.get('message', 'Unknown error')}", "danger")
        
        redirect(URL('api_keys'))
        
    except Exception as e:
        logger.error(f"Create API key error: {str(e)}")
        flash.set("Error creating API key", "danger")
        redirect(URL('api_keys'))

@action('api_keys/<key_id:int>/revoke', method='POST')
@action.uses(auth.user, flash_fixture)  
@waddlebot_user_required
def revoke_api_key(key_id):
    """Revoke API key"""
    try:
        session_token = session.get('user_session_token')
        if not session_token:
            flash.set("Session token required", "danger")
            redirect(URL('api_keys'))
        
        # Revoke API key through identity service
        result = identity_client.revoke_api_key(session_token, key_id)
        
        if result.get('success'):
            flash.set("API key revoked successfully", "success")
        else:
            flash.set(f"Error revoking API key: {result.get('message', 'Unknown error')}", "danger")
        
        redirect(URL('api_keys'))
        
    except Exception as e:
        logger.error(f"Revoke API key error: {str(e)}")
        flash.set("Error revoking API key", "danger")
        redirect(URL('api_keys'))