"""
WaddleBot Community Portal - py4web application with native py4web features
"""

from py4web import action, request, response, URL, Field, Session, DAL, redirect, HTTP, abort
from py4web.utils.form import Form, FormStyleBulma
from py4web.utils.grid import Grid, GridClassStyleBulma
from py4web.utils.auth import Auth, AuthJWT
from py4web.utils.mailer import Mailer
from py4web.utils.flash import Flash
from py4web.utils.cors import CORS
from py4web.core import Fixture
import os
import logging
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DB_URI = os.environ.get("DATABASE_URL", "sqlite://portal.db")
if DB_URI.startswith("postgres://"):
    DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)

# Initialize py4web components
db = DAL(DB_URI, pool_size=10, migrate=True, fake_migrate_all=False)
session = Session(storage=db)

# Enable CORS for API endpoints
CORS(origins=["*"])

# Configure mailer
mailer = Mailer(
    server=os.environ.get('SMTP_HOST', 'localhost'),
    sender=os.environ.get('FROM_EMAIL', 'noreply@waddlebot.com'),
    login=os.environ.get('SMTP_USERNAME', ''),
    password=os.environ.get('SMTP_PASSWORD', ''),
    tls=os.environ.get('SMTP_TLS', 'true').lower() == 'true',
    port=int(os.environ.get('SMTP_PORT', '587')),
    use_sendmail=not bool(os.environ.get('SMTP_HOST', ''))
)

# Configure auth with custom user fields
auth = Auth(session, db, mailer=mailer)

# Add custom fields to auth_user table
auth.db.auth_user.first_name.default = ''
auth.db.auth_user.last_name.default = ''

# Add custom fields for WaddleBot integration
auth.db.auth_user._add_field('waddlebot_user_id', 'string', unique=True)
auth.db.auth_user._add_field('display_name', 'string')
auth.db.auth_user._add_field('is_community_owner', 'boolean', default=False)
auth.db.auth_user._add_field('temp_password_expires', 'datetime')
auth.db.auth_user._add_field('created_by_command', 'boolean', default=False)
auth.db.auth_user._add_field('last_portal_login', 'datetime')

# Configure auth settings
auth.settings.login_url = URL('auth/login')
auth.settings.logout_url = URL('auth/logout')
auth.settings.profile_url = URL('auth/profile')
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.allow_basic_login = True
auth.settings.allow_delete_account = False
auth.settings.password_complexity = {"entropy": 0}  # Allow simple temp passwords
auth.settings.login_expiration_time = 3600 * 8  # 8 hours

# Flash messaging
flash = Flash(session)

# Import shared models and services
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from router_module.models import GLOBAL_COMMUNITY_ID
from router_module.services.rbac_service import rbac_service

# Create custom portal tables for extended functionality
db.define_table(
    'portal_community_access',
    Field('id', 'id'),
    Field('user_id', 'reference auth_user', required=True),
    Field('community_id', 'integer', required=True),
    Field('access_granted_at', 'datetime', default=datetime.utcnow),
    Field('access_granted_by', 'string'),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

db.define_table(
    'portal_temp_passwords',
    Field('id', 'id'),
    Field('waddlebot_user_id', 'string', required=True, unique=True),
    Field('temp_password', 'string', required=True),
    Field('email', 'string', required=True),
    Field('expires_at', 'datetime', required=True),
    Field('used', 'boolean', default=False),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Create indexes
try:
    db.executesql('CREATE INDEX IF NOT EXISTS idx_portal_community_access_user ON portal_community_access(user_id, community_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_portal_temp_passwords_user ON portal_temp_passwords(waddlebot_user_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_auth_user_waddlebot_id ON auth_user(waddlebot_user_id);')
except:
    pass

db.commit()

# Custom fixtures
class CommunityOwnerRequired(Fixture):
    """Fixture to require community owner access"""
    
    def on_request(self, context):
        if not auth.get_user():
            redirect(URL('auth/login'))
        
        user = auth.get_user()
        if not user.get('is_community_owner'):
            abort(403, "Community owner access required")

class WaddleBotUserRequired(Fixture):
    """Fixture to require WaddleBot user ID"""
    
    def on_request(self, context):
        if not auth.get_user():
            redirect(URL('auth/login'))
        
        user = auth.get_user()
        if not user.get('waddlebot_user_id'):
            abort(403, "WaddleBot user ID required")

# Initialize custom fixtures
community_owner_required = CommunityOwnerRequired()
waddlebot_user_required = WaddleBotUserRequired()

# Application constants
APP_NAME = "WaddleBot Community Portal"
PORTAL_URL = os.environ.get('PORTAL_URL', 'http://localhost:8000')

# Helper functions
def generate_temp_password() -> str:
    """Generate a temporary password"""
    return secrets.token_urlsafe(12)

def send_temp_password_email(email: str, waddlebot_user_id: str, temp_password: str) -> bool:
    """Send temporary password email using py4web mailer"""
    try:
        subject = "WaddleBot Community Portal - Temporary Password"
        
        body = f"""
Hello,

You have requested access to the WaddleBot Community Portal. Here are your login details:

WaddleBot User ID: {waddlebot_user_id}
Email: {email}
Temporary Password: {temp_password}

This temporary password will expire in 24 hours.

You can access the portal at: {PORTAL_URL}

If you did not request this access, please ignore this email.

Best regards,
The WaddleBot Team
"""
        
        mailer.send(
            to=email,
            subject=subject,
            body=body
        )
        
        logger.info(f"Temporary password email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending temp password email: {str(e)}")
        return False

def create_portal_user_from_command(waddlebot_user_id: str, email: str, display_name: str = None) -> Dict[str, Any]:
    """Create a portal user from chat command"""
    try:
        # Check if user already exists
        existing_user = db(db.auth_user.waddlebot_user_id == waddlebot_user_id).select().first()
        if existing_user:
            return {"success": False, "error": "User already exists"}
        
        # Generate temporary password
        temp_password = generate_temp_password()
        temp_expires = datetime.utcnow() + timedelta(hours=24)
        
        # Create user with py4web Auth
        user_id = auth.register(
            email=email,
            password=temp_password,
            first_name=display_name or waddlebot_user_id,
            last_name="",
            username=waddlebot_user_id
        )
        
        if user_id:
            # Update user with custom fields
            db(db.auth_user.id == user_id).update(
                waddlebot_user_id=waddlebot_user_id,
                display_name=display_name or waddlebot_user_id,
                is_community_owner=True,  # Users created via command are community owners
                temp_password_expires=temp_expires,
                created_by_command=True
            )
            
            # Store temp password record
            db.portal_temp_passwords.insert(
                waddlebot_user_id=waddlebot_user_id,
                temp_password=temp_password,
                email=email,
                expires_at=temp_expires
            )
            
            db.commit()
            
            # Send email
            email_sent = send_temp_password_email(email, waddlebot_user_id, temp_password)
            
            return {
                "success": True,
                "user_id": user_id,
                "temp_password": temp_password,
                "email_sent": email_sent
            }
        else:
            return {"success": False, "error": "Failed to create user"}
            
    except Exception as e:
        logger.error(f"Error creating portal user: {str(e)}")
        return {"success": False, "error": str(e)}

def get_user_communities(waddlebot_user_id: str) -> List[Dict[str, Any]]:
    """Get communities where user is an owner"""
    try:
        # Get all communities where user is owner
        communities = db(db.communities.is_active == True).select()
        
        user_communities = []
        for community in communities:
            # Check if user is owner
            user_role = rbac_service.get_user_role_in_community(waddlebot_user_id, community.id)
            if user_role == 'owner':
                user_communities.append({
                    "id": community.id,
                    "name": community.name,
                    "description": community.description,
                    "member_count": len(community.member_ids or []),
                    "entity_group_count": len(community.entity_groups or []),
                    "created_at": community.created_at,
                    "settings": community.settings or {}
                })
        
        return user_communities
        
    except Exception as e:
        logger.error(f"Error getting user communities: {str(e)}")
        return []

def get_community_members(community_id: int, waddlebot_user_id: str) -> List[Dict[str, Any]]:
    """Get community members with roles and reputation"""
    try:
        # Check if user is owner
        user_role = rbac_service.get_user_role_in_community(waddlebot_user_id, community_id)
        if user_role != 'owner':
            return []
        
        # Get community memberships
        memberships = db(
            (db.community_memberships.community_id == community_id) &
            (db.community_memberships.is_active == True)
        ).select()
        
        members = []
        for membership in memberships:
            member_user_id = membership.user_id
            
            # Get user role
            member_role = rbac_service.get_user_role_in_community(member_user_id, community_id)
            
            # Get user reputation
            reputation = db(
                (db.user_reputation.user_id == member_user_id) &
                (db.user_reputation.community_id == community_id)
            ).select().first()
            
            # Get display name from auth_user if available
            auth_user = db(db.auth_user.waddlebot_user_id == member_user_id).select().first()
            
            members.append({
                "user_id": member_user_id,
                "display_name": auth_user.display_name if auth_user else member_user_id,
                "role": member_role,
                "reputation": {
                    "current_score": reputation.current_score if reputation else 0,
                    "total_events": reputation.total_events if reputation else 0,
                    "last_activity": reputation.last_activity if reputation else None
                },
                "joined_at": membership.joined_at,
                "invited_by": membership.invited_by
            })
        
        return sorted(members, key=lambda x: x['reputation']['current_score'], reverse=True)
        
    except Exception as e:
        logger.error(f"Error getting community members: {str(e)}")
        return []

def get_community_modules(community_id: int, waddlebot_user_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get installed modules for community"""
    try:
        # Check if user is owner
        user_role = rbac_service.get_user_role_in_community(waddlebot_user_id, community_id)
        if user_role != 'owner':
            return {"core": [], "marketplace": []}
        
        # Get community entity groups
        community = db(
            (db.communities.id == community_id) &
            (db.communities.is_active == True)
        ).select().first()
        
        if not community:
            return {"core": [], "marketplace": []}
        
        # Get all entity IDs for this community
        entity_ids = []
        for group_id in (community.entity_groups or []):
            entity_group = db(
                (db.entity_groups.id == group_id) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if entity_group:
                entity_ids.extend(entity_group.entity_ids or [])
        
        # Get enabled commands/modules for these entities
        core_modules = []
        marketplace_modules = []
        
        if entity_ids:
            # Get all commands enabled for these entities
            commands = db(
                (db.command_permissions.entity_id.belongs(entity_ids)) &
                (db.command_permissions.is_enabled == True)
            ).select(
                db.command_permissions.ALL,
                db.commands.ALL,
                left=[db.commands.on(db.commands.id == db.command_permissions.command_id)]
            )
            
            for row in commands:
                command = row.commands
                permission = row.command_permissions
                
                if not command:
                    continue
                
                module_info = {
                    "id": command.id,
                    "command": command.command,
                    "prefix": command.prefix,
                    "description": command.description,
                    "module_type": command.module_type,
                    "location": command.location,
                    "version": command.version,
                    "is_active": command.is_active,
                    "usage_count": permission.usage_count,
                    "last_used": permission.last_used
                }
                
                if command.module_type == 'local':
                    core_modules.append(module_info)
                else:
                    marketplace_modules.append(module_info)
        
        return {
            "core": sorted(core_modules, key=lambda x: x['command']),
            "marketplace": sorted(marketplace_modules, key=lambda x: x['command'])
        }
        
    except Exception as e:
        logger.error(f"Error getting community modules: {str(e)}")
        return {"core": [], "marketplace": []}

# Update CLAUDE.md context note
CLAUDE_MD_CONTEXT = """
IMPORTANT: Always keep CLAUDE.md updated with any context changes!

The portal_module now uses py4web's native features:
- py4web Auth for user authentication and management
- py4web Mailer for email sending (SMTP/sendmail)
- py4web Forms for user input handling
- py4web Grid for data display
- py4web Flash for user notifications
- py4web Fixtures for access control

All portal functionality integrates with py4web's built-in systems while maintaining WaddleBot-specific features.
"""