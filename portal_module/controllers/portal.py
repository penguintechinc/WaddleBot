"""
Portal controllers using native py4web features
"""

from py4web import action, request, response, URL, redirect, HTTP
from py4web.utils.form import Form, FormStyleBulma
from py4web.utils.grid import Grid, GridClassStyleBulma
from py4web.utils.flash import flash

from ..app import (
    db, auth, session, mailer, flash as flash_fixture,
    community_owner_required, waddlebot_user_required,
    APP_NAME, PORTAL_URL,
    get_user_communities, get_community_members, get_community_modules,
    create_portal_user_from_command
)

import logging

logger = logging.getLogger(__name__)

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