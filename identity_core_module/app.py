"""
WaddleBot Identity Core Module
Cross-platform identity linking and verification system built on py4web Auth
"""

import os
import logging
from py4web import action, request, abort, response, Session, Cache, DAL, Field, HTTP, URL
from py4web.utils.auth import Auth, AuthEnforcer
from py4web.utils.auth_plugins.oauth2generic import OAuth2Generic
from py4web.utils.mailer import Mailer
from py4web.utils.form import Form, FormStyleBulma
from py4web.core import Fixture
from pydal.validators import *
from datetime import datetime, timedelta
import json
import requests
import secrets
import string
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import redis
import time
import traceback
from threading import Lock
import hashlib

# Import services
from .services.platform_service import PlatformService
from .services.verification_service import VerificationService
from .services.router_service import RouterService
from .config import Config
from .models import db
from .logging_config import setup_logging, log_event

# Setup logging
logger = setup_logging()

# Initialize Redis
try:
    redis_client = redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_DB,
        password=Config.REDIS_PASSWORD,
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Redis connection established")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

# Session
session = Session(secret=Config.SECRET_KEY)

# Configure py4web Auth with extended user fields
auth = Auth(
    session, 
    db,
    define_tables=True,
    use_username=True,
    registration_requires_confirmation=False,
    registration_requires_approval=False,
    allowed_actions=['all'],
    login_expiration_time=3600,
    password_complexity={'entropy': 50},
    block_previous_password_num=3,
    expose_all_models=False
)

# Extend auth_user table with WaddleBot specific fields
auth.define_tables()

# Add custom fields to auth_user if they don't exist
if 'waddlebot_display_name' not in db.auth_user:
    db.auth_user.waddlebot_display_name = Field('waddlebot_display_name', length=64)
if 'primary_platform' not in db.auth_user:
    db.auth_user.primary_platform = Field('primary_platform', length=20)
if 'reputation_score' not in db.auth_user:
    db.auth_user.reputation_score = Field('reputation_score', 'integer', default=0)
if 'metadata' not in db.auth_user:
    db.auth_user.metadata = Field('metadata', 'json', default={})

# Configure OAuth providers if enabled
oauth_providers = {}
if Config.ENABLE_OAUTH_PROVIDERS:
    # Twitch OAuth
    if Config.OAUTH_PROVIDERS['twitch']['enabled'] and Config.OAUTH_PROVIDERS['twitch']['client_id']:
        oauth_providers['twitch'] = OAuth2Generic(
            client_id=Config.OAUTH_PROVIDERS['twitch']['client_id'],
            client_secret=Config.OAUTH_PROVIDERS['twitch']['client_secret'],
            authorize_url=Config.OAUTH_PROVIDERS['twitch']['authorize_url'],
            access_token_url=Config.OAUTH_PROVIDERS['twitch']['token_url'],
            callback_url=Config.OAUTH_PROVIDERS['twitch']['redirect_uri'],
            scope_delimiter=' ',
            scopes=Config.OAUTH_PROVIDERS['twitch']['scope'],
            maps={
                'email': lambda data: data.get('email', ''),
                'first_name': lambda data: data.get('display_name', '').split()[0] if data.get('display_name') else '',
                'last_name': lambda data: ' '.join(data.get('display_name', '').split()[1:]) if data.get('display_name') else '',
                'username': lambda data: data.get('login', ''),
                'sso_id': lambda data: data.get('id', ''),
                'picture': lambda data: data.get('profile_image_url', '')
            },
            user_info_url=Config.OAUTH_PROVIDERS['twitch']['user_info_url'],
            user_info_headers={'Client-ID': Config.OAUTH_PROVIDERS['twitch']['client_id']}
        )
    
    # Discord OAuth
    if Config.OAUTH_PROVIDERS['discord']['enabled'] and Config.OAUTH_PROVIDERS['discord']['client_id']:
        oauth_providers['discord'] = OAuth2Generic(
            client_id=Config.OAUTH_PROVIDERS['discord']['client_id'],
            client_secret=Config.OAUTH_PROVIDERS['discord']['client_secret'],
            authorize_url=Config.OAUTH_PROVIDERS['discord']['authorize_url'],
            access_token_url=Config.OAUTH_PROVIDERS['discord']['token_url'],
            callback_url=Config.OAUTH_PROVIDERS['discord']['redirect_uri'],
            scope_delimiter=' ',
            scopes=Config.OAUTH_PROVIDERS['discord']['scope'],
            maps={
                'email': lambda data: data.get('email', ''),
                'first_name': lambda data: data.get('global_name', '').split()[0] if data.get('global_name') else data.get('username', ''),
                'last_name': lambda data: ' '.join(data.get('global_name', '').split()[1:]) if data.get('global_name') else '',
                'username': lambda data: data.get('username', ''),
                'sso_id': lambda data: data.get('id', ''),
                'picture': lambda data: f"https://cdn.discordapp.com/avatars/{data.get('id')}/{data.get('avatar')}.png" if data.get('avatar') else ''
            },
            user_info_url=Config.OAUTH_PROVIDERS['discord']['user_info_url']
        )
    
    # Slack OAuth
    if Config.OAUTH_PROVIDERS['slack']['enabled'] and Config.OAUTH_PROVIDERS['slack']['client_id']:
        oauth_providers['slack'] = OAuth2Generic(
            client_id=Config.OAUTH_PROVIDERS['slack']['client_id'],
            client_secret=Config.OAUTH_PROVIDERS['slack']['client_secret'],
            authorize_url=Config.OAUTH_PROVIDERS['slack']['authorize_url'],
            access_token_url=Config.OAUTH_PROVIDERS['slack']['token_url'],
            callback_url=Config.OAUTH_PROVIDERS['slack']['redirect_uri'],
            scope_delimiter=' ',
            scopes=Config.OAUTH_PROVIDERS['slack']['scope'],
            maps={
                'email': lambda data: data.get('user', {}).get('email', ''),
                'first_name': lambda data: data.get('user', {}).get('name', '').split()[0] if data.get('user', {}).get('name') else '',
                'last_name': lambda data: ' '.join(data.get('user', {}).get('name', '').split()[1:]) if data.get('user', {}).get('name') else '',
                'username': lambda data: data.get('user', {}).get('name', ''),
                'sso_id': lambda data: data.get('user', {}).get('id', ''),
                'picture': lambda data: data.get('user', {}).get('image_72', '')
            },
            user_info_url=Config.OAUTH_PROVIDERS['slack']['user_info_url']
        )

# Register OAuth providers with auth
for provider_name, provider in oauth_providers.items():
    auth.register_plugin(provider)

# Configure mailer for email verification
mail = Mailer(
    server=Config.SMTP_HOST,
    sender=Config.FROM_EMAIL,
    login=f"{Config.SMTP_USERNAME}:{Config.SMTP_PASSWORD}",
    tls=Config.SMTP_TLS
)

# Initialize services
platform_service = PlatformService()
verification_service = VerificationService(redis_client)
router_service = RouterService()

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)

# Auth enforcer for py4web auth
auth_enforcer = AuthEnforcer(auth)

# API Key authentication decorator
def requires_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            log_event("AUTH", "API", action="auth_failed", 
                     details={"reason": "No API key provided"})
            abort(401, "API key required")
        
        # Check if it's a system API key
        if api_key in Config.VALID_API_KEYS:
            return f(*args, **kwargs)
        
        # Check if it's a user API key
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        user_key = db((db.user_api_keys.api_key_hash == api_key_hash) & 
                     (db.user_api_keys.is_active == True) &
                     (db.user_api_keys.expires_at > datetime.utcnow())).select().first()
        
        if not user_key:
            log_event("AUTH", "API", action="auth_failed", 
                     details={"reason": "Invalid API key"})
            abort(401, "Invalid or expired API key")
        
        # Update last used
        user_key.update_record(
            last_used_at=datetime.utcnow(),
            usage_count=(user_key.usage_count or 0) + 1
        )
        db.commit()
        
        # Set user context
        request.waddlebot_user_id = user_key.user_id
        request.api_key_id = user_key.id
        
        return f(*args, **kwargs)
    return decorated_function

@action("index", method=["GET"])
@action.uses(session)
def index():
    """Module information endpoint"""
    return {
        "module": Config.MODULE_NAME,
        "version": Config.MODULE_VERSION,
        "description": "Cross-platform identity linking and verification system with py4web Auth",
        "oauth_providers": {
            name: {
                "enabled": config["enabled"],
                "authorize_url": URL(f"auth/oauth/{name}")
            }
            for name, config in Config.OAUTH_PROVIDERS.items()
            if config["enabled"] and config["client_id"]
        },
        "endpoints": {
            # Platform Linking
            "POST /identity/link": "Initiate identity linking",
            "POST /identity/verify": "Verify identity with code",
            "GET /identity/user/<user_id>": "Get user's linked identities",
            "GET /identity/platform/<platform>/<platform_id>": "Get user ID for platform user",
            "DELETE /identity/unlink": "Unlink a platform identity",
            "GET /identity/pending": "Get pending verifications",
            "POST /identity/resend": "Resend verification code",
            
            # API Key Management
            "POST /identity/api-keys": "Create API key for user",
            "GET /identity/api-keys": "List user's API keys",
            "DELETE /identity/api-keys/<key_id>": "Revoke API key",
            "POST /identity/api-keys/<key_id>/regenerate": "Regenerate API key",
            
            # User Management (py4web Auth)
            "POST /auth/register": "Register new user",
            "POST /auth/login": "Login user",
            "POST /auth/logout": "Logout user",
            "GET /auth/profile": "Get user profile",
            "PUT /auth/profile": "Update user profile",
            "POST /auth/change-password": "Change password",
            "POST /auth/request-reset-password": "Request password reset",
            
            # OAuth Authentication
            "GET /auth/oauth/<provider>": "Initiate OAuth login with provider",
            "GET /auth/oauth/<provider>/callback": "OAuth callback handler",
            
            # Admin
            "GET /identity/stats": "Get identity statistics",
            "GET /health": "Health check"
        }
    }

@action("health", method=["GET"])
def health():
    """Health check endpoint"""
    try:
        # Check database
        db.executesql("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Redis
    redis_status = "healthy" if redis_client and redis_client.ping() else "unhealthy"
    
    # Check external services
    services_status = platform_service.health_check()
    
    status = "healthy" if all([
        db_status == "healthy",
        redis_status == "healthy",
        all(s["status"] == "healthy" for s in services_status.values())
    ]) else "unhealthy"
    
    return {
        "status": status,
        "module": Config.MODULE_NAME,
        "version": Config.MODULE_VERSION,
        "components": {
            "database": db_status,
            "redis": redis_status,
            "services": services_status
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# ============ Platform Linking Endpoints ============

@action("identity/link", method=["POST"])
@action.uses(session, db, auth_enforcer)
@requires_api_key
def link_identity():
    """
    Initiate identity linking between platforms
    
    Expected JSON:
    {
        "source_platform": "discord",
        "target_platform": "twitch",
        "target_username": "penguinzplays"
    }
    """
    try:
        data = request.json
        if not data:
            abort(400, "No data provided")
        
        # Get current user
        user_id = auth.user_id if auth.user_id else request.waddlebot_user_id
        if not user_id:
            abort(401, "User not authenticated")
        
        # Validate required fields
        required = ["source_platform", "target_platform", "target_username"]
        for field in required:
            if field not in data:
                abort(400, f"Missing required field: {field}")
        
        source_platform = data["source_platform"].lower()
        target_platform = data["target_platform"].lower()
        target_username = data["target_username"]
        
        # Validate platforms
        valid_platforms = ["twitch", "discord", "slack"]
        if source_platform not in valid_platforms or target_platform not in valid_platforms:
            abort(400, "Invalid platform specified")
        
        if source_platform == target_platform:
            abort(400, "Source and target platforms cannot be the same")
        
        # Check if source identity is already verified
        source_identity = db((db.platform_identities.user_id == user_id) & 
                           (db.platform_identities.platform == source_platform) &
                           (db.platform_identities.is_verified == True)).select().first()
        
        if not source_identity:
            abort(400, f"User must first verify their {source_platform} identity")
        
        # Check if target identity already exists
        existing_target = db((db.platform_identities.user_id == user_id) & 
                           (db.platform_identities.platform == target_platform) &
                           (db.platform_identities.is_verified == True)).select().first()
        
        if existing_target:
            abort(400, f"{target_platform} identity already linked")
        
        # Generate verification code
        verification_code = verification_service.generate_code()
        
        # Create or update pending verification
        pending = db((db.identity_verifications.user_id == user_id) & 
                    (db.identity_verifications.target_platform == target_platform) &
                    (db.identity_verifications.status == "pending")).select().first()
        
        if pending:
            # Update existing pending verification
            pending.update_record(
                target_username=target_username,
                verification_code=verification_code,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=Config.VERIFICATION_TIMEOUT_MINUTES)
            )
        else:
            # Create new verification request
            db.identity_verifications.insert(
                user_id=user_id,
                source_platform=source_platform,
                source_username=source_identity.platform_username,
                target_platform=target_platform,
                target_username=target_username,
                verification_code=verification_code,
                status="pending",
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=Config.VERIFICATION_TIMEOUT_MINUTES)
            )
        
        db.commit()
        
        # Send verification code via whisper/DM
        executor.submit(
            platform_service.send_verification_message,
            target_platform,
            target_username,
            verification_code,
            source_platform,
            source_identity.platform_username
        )
        
        log_event("IDENTITY", "LINK", 
                 user_id=user_id,
                 action="link_initiated",
                 result="success",
                 details={
                     "source_platform": source_platform,
                     "target_platform": target_platform,
                     "target_username": target_username
                 })
        
        return {
            "success": True,
            "message": f"Verification code sent to {target_username} on {target_platform}",
            "expires_in_minutes": Config.VERIFICATION_TIMEOUT_MINUTES
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in link_identity: {e}", exc_info=True)
        log_event("ERROR", "IDENTITY", 
                 action="link_failed",
                 result="error",
                 details={"error": str(e)})
        abort(500, "Internal server error")

@action("identity/verify", method=["POST"])
@action.uses(session, db)
@requires_api_key
def verify_identity():
    """
    Verify identity with code (called by platform collectors)
    
    Expected JSON:
    {
        "platform": "twitch",
        "platform_id": "123456",
        "platform_username": "penguinzplays",
        "verification_code": "ABC123"
    }
    """
    try:
        data = request.json
        if not data:
            abort(400, "No data provided")
        
        # Validate required fields
        required = ["platform", "platform_id", "platform_username", "verification_code"]
        for field in required:
            if field not in data:
                abort(400, f"Missing required field: {field}")
        
        platform = data["platform"].lower()
        platform_id = str(data["platform_id"])
        platform_username = data["platform_username"]
        verification_code = data["verification_code"].upper()
        
        # Find pending verification
        verification = db((db.identity_verifications.target_platform == platform) &
                        (db.identity_verifications.target_username == platform_username) &
                        (db.identity_verifications.verification_code == verification_code) &
                        (db.identity_verifications.status == "pending") &
                        (db.identity_verifications.expires_at > datetime.utcnow())).select().first()
        
        if not verification:
            log_event("AUTH", "IDENTITY", 
                     platform=platform,
                     user=platform_username,
                     action="verify_failed",
                     result="invalid_code")
            abort(400, "Invalid or expired verification code")
        
        # Check if this platform_id is already linked to another user
        existing = db((db.platform_identities.platform == platform) &
                     (db.platform_identities.platform_id == platform_id) &
                     (db.platform_identities.is_verified == True)).select().first()
        
        if existing and existing.user_id != verification.user_id:
            abort(400, f"This {platform} account is already linked to another WaddleBot user")
        
        # Create or update platform identity
        identity = db((db.platform_identities.user_id == verification.user_id) &
                     (db.platform_identities.platform == platform)).select().first()
        
        if identity:
            identity.update_record(
                platform_id=platform_id,
                platform_username=platform_username,
                is_verified=True,
                verified_at=datetime.utcnow(),
                verification_method="whisper"
            )
        else:
            db.platform_identities.insert(
                user_id=verification.user_id,
                platform=platform,
                platform_id=platform_id,
                platform_username=platform_username,
                is_verified=True,
                verified_at=datetime.utcnow(),
                verification_method="whisper"
            )
        
        # Update verification status
        verification.update_record(
            status="completed",
            verified_at=datetime.utcnow(),
            target_platform_id=platform_id
        )
        
        # Update user's primary platform if not set
        user = db.auth_user[verification.user_id]
        if user and not user.primary_platform:
            user.update_record(primary_platform=platform)
        
        db.commit()
        
        # Cache the mapping
        if redis_client:
            cache_key = f"identity:{platform}:{platform_id}"
            redis_client.setex(cache_key, Config.CACHE_TTL, verification.user_id)
        
        log_event("IDENTITY", "VERIFY", 
                 user_id=verification.user_id,
                 platform=platform,
                 user=platform_username,
                 action="verify_success",
                 result="success")
        
        return {
            "success": True,
            "message": f"{platform} identity successfully linked",
            "user_id": verification.user_id
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in verify_identity: {e}", exc_info=True)
        log_event("ERROR", "IDENTITY", 
                 action="verify_failed",
                 result="error",
                 details={"error": str(e)})
        abort(500, "Internal server error")

# ============ OAuth Authentication Endpoints ============

@action("auth/oauth/<provider>", method=["GET"])
@action.uses(session, db)
def oauth_login(provider):
    """Initiate OAuth login with provider"""
    try:
        provider = provider.lower()
        
        # Validate provider
        if provider not in oauth_providers:
            abort(400, f"Unsupported OAuth provider: {provider}")
        
        # Get OAuth provider instance
        oauth_provider = oauth_providers[provider]
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        session['oauth_provider'] = provider
        
        # Build authorization URL
        auth_url = oauth_provider.get_login_url(state=state)
        
        log_event("AUTH", "OAUTH", 
                 action="oauth_initiated",
                 result="success",
                 details={"provider": provider})
        
        # Redirect to provider
        return response.headers.update({"Location": auth_url}), 302
        
    except Exception as e:
        logger.error(f"Error in oauth_login: {e}", exc_info=True)
        log_event("ERROR", "OAUTH", 
                 action="oauth_initiate_failed",
                 result="error",
                 details={"provider": provider, "error": str(e)})
        abort(500, "OAuth initiation failed")

@action("auth/oauth/<provider>/callback", method=["GET"])
@action.uses(session, db)
def oauth_callback(provider):
    """Handle OAuth callback from provider"""
    try:
        provider = provider.lower()
        
        # Validate provider
        if provider not in oauth_providers:
            abort(400, f"Unsupported OAuth provider: {provider}")
        
        # Validate state parameter
        received_state = request.query.get('state')
        expected_state = session.get('oauth_state')
        expected_provider = session.get('oauth_provider')
        
        if not received_state or received_state != expected_state or expected_provider != provider:
            log_event("AUTH", "OAUTH", 
                     action="oauth_callback_failed",
                     result="invalid_state",
                     details={"provider": provider})
            abort(400, "Invalid state parameter")
        
        # Clear session state
        session.pop('oauth_state', None)
        session.pop('oauth_provider', None)
        
        # Get authorization code
        code = request.query.get('code')
        if not code:
            error = request.query.get('error')
            log_event("AUTH", "OAUTH", 
                     action="oauth_callback_failed",
                     result="no_code",
                     details={"provider": provider, "error": error})
            abort(400, f"OAuth error: {error or 'No authorization code'}")
        
        # Get OAuth provider instance
        oauth_provider = oauth_providers[provider]
        
        # Exchange code for token and get user info
        try:
            user_data = oauth_provider.get_user_info(code)
        except Exception as e:
            logger.error(f"Failed to get user info from {provider}: {e}")
            log_event("AUTH", "OAUTH", 
                     action="oauth_user_info_failed",
                     result="error",
                     details={"provider": provider, "error": str(e)})
            abort(400, f"Failed to get user information from {provider}")
        
        # Extract user information
        platform_id = user_data.get('sso_id', '')
        username = user_data.get('username', '')
        email = user_data.get('email', '')
        display_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        
        if not platform_id or not username:
            log_event("AUTH", "OAUTH", 
                     action="oauth_callback_failed",
                     result="missing_user_data",
                     details={"provider": provider})
            abort(400, "Insufficient user data from provider")
        
        # Check if platform identity already exists
        existing_identity = db((db.platform_identities.platform == provider) &
                             (db.platform_identities.platform_id == platform_id) &
                             (db.platform_identities.is_verified == True)).select().first()
        
        if existing_identity:
            # User exists - log them in
            user = db.auth_user[existing_identity.user_id]
            if user:
                auth.login_user(user)
                
                log_event("AUTH", "OAUTH", 
                         user_id=user.id,
                         platform=provider,
                         action="oauth_login_success",
                         result="existing_user")
                
                return {
                    "success": True,
                    "message": f"Logged in via {provider.title()}",
                    "user_id": user.id,
                    "redirect": "/dashboard"
                }
        
        # Check if user already exists by email
        existing_user = None
        if email:
            existing_user = db(db.auth_user.email == email).select().first()
        
        if existing_user:
            # Link this OAuth account to existing user
            user_id = existing_user.id
        else:
            # Create new user account
            try:
                user_data_for_creation = {
                    'username': username,
                    'email': email or f"{username}@{provider}.oauth",
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', ''),
                    'waddlebot_display_name': display_name or username,
                    'primary_platform': provider,
                    'password': secrets.token_urlsafe(32)  # Random password since they'll use OAuth
                }
                
                user_id = db.auth_user.insert(**user_data_for_creation)
                db.commit()
                
                log_event("AUTH", "OAUTH", 
                         user_id=user_id,
                         platform=provider,
                         action="oauth_user_created",
                         result="success")
                
            except Exception as e:
                logger.error(f"Failed to create user: {e}")
                log_event("ERROR", "OAUTH", 
                         action="oauth_user_creation_failed",
                         result="error",
                         details={"provider": provider, "error": str(e)})
                abort(500, "Failed to create user account")
        
        # Create/update platform identity
        identity = db((db.platform_identities.user_id == user_id) &
                     (db.platform_identities.platform == provider)).select().first()
        
        if identity:
            identity.update_record(
                platform_id=platform_id,
                platform_username=username,
                is_verified=True,
                verified_at=datetime.utcnow(),
                verification_method="oauth"
            )
        else:
            db.platform_identities.insert(
                user_id=user_id,
                platform=provider,
                platform_id=platform_id,
                platform_username=username,
                is_verified=True,
                verified_at=datetime.utcnow(),
                verification_method="oauth"
            )
        
        # Store OAuth user data cache
        cache_record = db((db.oauth_user_cache.user_id == user_id) &
                         (db.oauth_user_cache.provider == provider)).select().first()
        
        if cache_record:
            cache_record.update_record(
                provider_user_id=platform_id,
                provider_username=username,
                provider_email=email,
                provider_display_name=display_name,
                provider_avatar_url=user_data.get('picture', ''),
                raw_user_data=user_data,
                last_updated=datetime.utcnow()
            )
        else:
            db.oauth_user_cache.insert(
                user_id=user_id,
                provider=provider,
                provider_user_id=platform_id,
                provider_username=username,
                provider_email=email,
                provider_display_name=display_name,
                provider_avatar_url=user_data.get('picture', ''),
                raw_user_data=user_data,
                last_updated=datetime.utcnow()
            )
        
        db.commit()
        
        # Update cache
        if redis_client:
            cache_key = f"identity:{provider}:{platform_id}"
            redis_client.setex(cache_key, Config.CACHE_TTL, user_id)
        
        # Log the user in
        user = db.auth_user[user_id]
        auth.login_user(user)
        
        log_event("AUTH", "OAUTH", 
                 user_id=user_id,
                 platform=provider,
                 action="oauth_login_success",
                 result="success")
        
        return {
            "success": True,
            "message": f"Successfully authenticated via {provider.title()}",
            "user_id": user_id,
            "redirect": "/dashboard"
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in oauth_callback: {e}", exc_info=True)
        log_event("ERROR", "OAUTH", 
                 action="oauth_callback_failed",
                 result="error",
                 details={"provider": provider, "error": str(e)})
        abort(500, "OAuth callback failed")

# ============ Web Interface Routes ============

@action("login", method=["GET", "POST"])
@action("auth/login", method=["GET", "POST"])
@action.uses(session, db, "oauth_login.html")
def web_login():
    """Web interface for OAuth login"""
    if auth.user_id:
        # Already logged in, redirect to dashboard
        redirect(URL('dashboard'))
    
    # Prepare OAuth provider info for template
    enabled_providers = {}
    for name, config in Config.OAUTH_PROVIDERS.items():
        if config["enabled"] and config["client_id"]:
            enabled_providers[name] = {
                "enabled": True,
                "login_url": URL(f"auth/oauth/{name}")
            }
    
    return {
        "oauth_providers": enabled_providers,
        "ENABLE_OAUTH_PROVIDERS": Config.ENABLE_OAUTH_PROVIDERS
    }

@action("dashboard", method=["GET"])
@action.uses(session, db, auth_enforcer, "dashboard.html")
def dashboard():
    """User dashboard showing linked identities and API keys"""
    user = auth.get_user()
    
    # Get linked platforms
    platforms = db((db.platform_identities.user_id == user['id']) &
                  (db.platform_identities.is_verified == True)).select()
    
    # Get API keys
    api_keys = db((db.user_api_keys.user_id == user['id']) &
                 (db.user_api_keys.is_active == True)).select(
                     orderby=~db.user_api_keys.created_at)
    
    # Get OAuth cached data
    oauth_data = {}
    for platform in platforms:
        oauth_cache = db((db.oauth_user_cache.user_id == user['id']) &
                        (db.oauth_user_cache.provider == platform.platform)).select().first()
        if oauth_cache:
            oauth_data[platform.platform] = {
                'avatar_url': oauth_cache.provider_avatar_url,
                'display_name': oauth_cache.provider_display_name
            }
    
    return {
        "user": user,
        "platforms": platforms,
        "api_keys": api_keys,
        "oauth_data": oauth_data
    }

@action("identity/user/<user_id>", method=["GET"])
@action.uses(session, db)
@requires_api_key
def get_user_identities(user_id):
    """Get all linked identities for a user"""
    try:
        # Get user info
        user = db.auth_user[int(user_id)]
        if not user:
            abort(404, "User not found")
        
        # Get linked platforms
        identities = db((db.platform_identities.user_id == user_id) &
                       (db.platform_identities.is_verified == True)).select()
        
        result = {
            "user_id": user_id,
            "username": user.username,
            "display_name": user.waddlebot_display_name or user.username,
            "email": user.email,
            "primary_platform": user.primary_platform,
            "reputation_score": user.reputation_score or 0,
            "identities": []
        }
        
        for identity in identities:
            result["identities"].append({
                "platform": identity.platform,
                "platform_id": identity.platform_id,
                "platform_username": identity.platform_username,
                "verified_at": identity.verified_at.isoformat() if identity.verified_at else None,
                "verification_method": identity.verification_method
            })
        
        return result
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_identities: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("identity/platform/<platform>/<platform_id>", method=["GET"])
@action.uses(session, db)
@requires_api_key
def get_user_by_platform(platform, platform_id):
    """Get user ID for a platform user"""
    try:
        # Check cache first
        if redis_client:
            cache_key = f"identity:{platform}:{platform_id}"
            cached = redis_client.get(cache_key)
            if cached:
                user = db.auth_user[int(cached)]
                if user:
                    return {
                        "user_id": cached,
                        "username": user.username,
                        "display_name": user.waddlebot_display_name or user.username,
                        "platform": platform,
                        "platform_id": platform_id
                    }
        
        # Query database
        identity = db((db.platform_identities.platform == platform) &
                     (db.platform_identities.platform_id == str(platform_id)) &
                     (db.platform_identities.is_verified == True)).select().first()
        
        if not identity:
            abort(404, "Identity not found")
        
        user = db.auth_user[identity.user_id]
        if not user:
            abort(404, "User not found")
        
        # Update cache
        if redis_client:
            cache_key = f"identity:{platform}:{platform_id}"
            redis_client.setex(cache_key, Config.CACHE_TTL, identity.user_id)
        
        return {
            "user_id": identity.user_id,
            "username": user.username,
            "display_name": user.waddlebot_display_name or user.username,
            "platform": platform,
            "platform_id": platform_id,
            "platform_username": identity.platform_username
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_by_platform: {e}", exc_info=True)
        abort(500, "Internal server error")

# ============ API Key Management Endpoints ============

@action("identity/api-keys", method=["POST"])
@action.uses(session, db, auth_enforcer)
def create_api_key():
    """
    Create API key for authenticated user
    
    Expected JSON:
    {
        "name": "My Bot Key",
        "expires_in_days": 365  # optional, default 365
    }
    """
    try:
        data = request.json or {}
        
        user_id = auth.user_id
        if not user_id:
            abort(401, "User not authenticated")
        
        name = data.get("name", "API Key")
        expires_in_days = data.get("expires_in_days", 365)
        
        # Check key limit
        active_keys = db((db.user_api_keys.user_id == user_id) &
                        (db.user_api_keys.is_active == True)).count()
        
        if active_keys >= Config.MAX_API_KEYS_PER_USER:
            abort(400, f"Maximum {Config.MAX_API_KEYS_PER_USER} active API keys allowed")
        
        # Generate API key
        api_key = f"wbot_user_{secrets.token_urlsafe(32)}"
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Create key record
        key_id = db.user_api_keys.insert(
            user_id=user_id,
            name=name,
            api_key_hash=api_key_hash,
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )
        db.commit()
        
        log_event("API_KEY", "CREATE", 
                 user_id=user_id,
                 action="api_key_created",
                 result="success",
                 details={"key_id": key_id, "name": name})
        
        return {
            "success": True,
            "key_id": key_id,
            "api_key": api_key,  # Only shown once!
            "name": name,
            "expires_at": (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat(),
            "warning": "Save this API key securely. It won't be shown again!"
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in create_api_key: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("identity/api-keys", method=["GET"])
@action.uses(session, db, auth_enforcer)
def list_api_keys():
    """List user's API keys"""
    try:
        user_id = auth.user_id
        if not user_id:
            abort(401, "User not authenticated")
        
        keys = db((db.user_api_keys.user_id == user_id) &
                 (db.user_api_keys.is_active == True)).select(
                     orderby=~db.user_api_keys.created_at)
        
        result = []
        for key in keys:
            result.append({
                "key_id": key.id,
                "name": key.name,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "usage_count": key.usage_count or 0
            })
        
        return {"api_keys": result}
        
    except Exception as e:
        logger.error(f"Error in list_api_keys: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("identity/api-keys/<key_id>", method=["DELETE"])
@action.uses(session, db, auth_enforcer)
def revoke_api_key(key_id):
    """Revoke API key"""
    try:
        user_id = auth.user_id
        if not user_id:
            abort(401, "User not authenticated")
        
        # Find key
        api_key = db((db.user_api_keys.id == key_id) &
                    (db.user_api_keys.user_id == user_id)).select().first()
        
        if not api_key:
            abort(404, "API key not found")
        
        # Revoke key
        api_key.update_record(
            is_active=False,
            revoked_at=datetime.utcnow()
        )
        db.commit()
        
        log_event("API_KEY", "REVOKE", 
                 user_id=user_id,
                 action="api_key_revoked",
                 result="success",
                 details={"key_id": key_id})
        
        return {
            "success": True,
            "message": "API key revoked successfully"
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in revoke_api_key: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("identity/api-keys/<key_id>/regenerate", method=["POST"])
@action.uses(session, db, auth_enforcer)
def regenerate_api_key(key_id):
    """Regenerate API key"""
    try:
        user_id = auth.user_id
        if not user_id:
            abort(401, "User not authenticated")
        
        # Find key
        api_key = db((db.user_api_keys.id == key_id) &
                    (db.user_api_keys.user_id == user_id) &
                    (db.user_api_keys.is_active == True)).select().first()
        
        if not api_key:
            abort(404, "API key not found")
        
        # Generate new key
        new_api_key = f"wbot_user_{secrets.token_urlsafe(32)}"
        new_api_key_hash = hashlib.sha256(new_api_key.encode()).hexdigest()
        
        # Update key
        api_key.update_record(
            api_key_hash=new_api_key_hash,
            regenerated_at=datetime.utcnow()
        )
        db.commit()
        
        log_event("API_KEY", "REGENERATE", 
                 user_id=user_id,
                 action="api_key_regenerated",
                 result="success",
                 details={"key_id": key_id})
        
        return {
            "success": True,
            "api_key": new_api_key,
            "message": "API key regenerated successfully",
            "warning": "Save this API key securely. It won't be shown again!"
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in regenerate_api_key: {e}", exc_info=True)
        abort(500, "Internal server error")

# ============ py4web Auth Wrappers ============

@action("auth/register", method=["POST"])
@action.uses(session, db)
def register():
    """Register new user"""
    try:
        data = request.json
        if not data:
            abort(400, "No data provided")
        
        # Validate required fields
        required = ["username", "email", "password"]
        for field in required:
            if field not in data:
                abort(400, f"Missing required field: {field}")
        
        # Check if username/email already exists
        if db(db.auth_user.username == data["username"]).count():
            abort(400, "Username already exists")
        
        if db(db.auth_user.email == data["email"]).count():
            abort(400, "Email already exists")
        
        # Register user through py4web auth
        user = auth.register(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            waddlebot_display_name=data.get("display_name", data["username"])
        )
        
        if not user:
            abort(400, "Registration failed")
        
        log_event("AUTH", "REGISTER", 
                 user_id=user['id'],
                 action="user_registered",
                 result="success",
                 details={"username": data["username"]})
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": user['id']
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in register: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("auth/login", method=["POST"])
@action.uses(session, db)
def login():
    """Login user"""
    try:
        data = request.json
        if not data:
            abort(400, "No data provided")
        
        username = data.get("username") or data.get("email")
        password = data.get("password")
        
        if not username or not password:
            abort(400, "Username/email and password required")
        
        # Login through py4web auth
        user = auth.login(username, password)
        
        if not user:
            log_event("AUTH", "LOGIN", 
                     action="login_failed",
                     result="invalid_credentials",
                     details={"username": username})
            abort(401, "Invalid credentials")
        
        log_event("AUTH", "LOGIN", 
                 user_id=user['id'],
                 action="login_success",
                 result="success")
        
        return {
            "success": True,
            "message": "Login successful",
            "user_id": user['id'],
            "username": user['username']
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in login: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("auth/logout", method=["POST"])
@action.uses(session, db, auth_enforcer)
def logout():
    """Logout user"""
    try:
        user_id = auth.user_id
        auth.logout()
        
        log_event("AUTH", "LOGOUT", 
                 user_id=user_id,
                 action="logout_success",
                 result="success")
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Error in logout: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("auth/profile", method=["GET"])
@action.uses(session, db, auth_enforcer)
def get_profile():
    """Get user profile"""
    try:
        user = auth.get_user()
        if not user:
            abort(404, "User not found")
        
        # Get linked platforms
        platforms = db((db.platform_identities.user_id == user['id']) &
                      (db.platform_identities.is_verified == True)).select()
        
        return {
            "user_id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "display_name": user.get('waddlebot_display_name') or user['username'],
            "first_name": user.get('first_name', ''),
            "last_name": user.get('last_name', ''),
            "primary_platform": user.get('primary_platform'),
            "reputation_score": user.get('reputation_score', 0),
            "platforms": [p.platform for p in platforms],
            "created_at": user.get('created_on').isoformat() if user.get('created_on') else None
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in get_profile: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("auth/profile", method=["PUT"])
@action.uses(session, db, auth_enforcer)
def update_profile():
    """Update user profile"""
    try:
        data = request.json
        if not data:
            abort(400, "No data provided")
        
        user_id = auth.user_id
        user = db.auth_user[user_id]
        if not user:
            abort(404, "User not found")
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'waddlebot_display_name', 'primary_platform']
        update_data = {}
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if update_data:
            user.update_record(**update_data)
            db.commit()
        
        log_event("AUTH", "PROFILE", 
                 user_id=user_id,
                 action="profile_updated",
                 result="success",
                 details=update_data)
        
        return {
            "success": True,
            "message": "Profile updated successfully"
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in update_profile: {e}", exc_info=True)
        abort(500, "Internal server error")

@action("identity/stats", method=["GET"])
@action.uses(session, db)
@requires_api_key
def get_stats():
    """Get identity module statistics"""
    try:
        stats = {
            "total_users": db(db.auth_user).count(),
            "verified_identities": db(db.platform_identities.is_verified == True).count(),
            "pending_verifications": db((db.identity_verifications.status == "pending") &
                                      (db.identity_verifications.expires_at > datetime.utcnow())).count(),
            "active_api_keys": db(db.user_api_keys.is_active == True).count(),
            "platforms": {}
        }
        
        # Platform breakdown
        for platform in ["twitch", "discord", "slack"]:
            stats["platforms"][platform] = db((db.platform_identities.platform == platform) &
                                            (db.platform_identities.is_verified == True)).count()
        
        # Multi-platform users
        multi_platform = db.executesql("""
            SELECT COUNT(DISTINCT user_id) 
            FROM platform_identities 
            WHERE is_verified = 'T'
            GROUP BY user_id 
            HAVING COUNT(DISTINCT platform) > 1
        """)
        stats["multi_platform_users"] = len(multi_platform) if multi_platform else 0
        
        return stats
        
    except Exception as e:
        logger.error(f"Error in get_stats: {e}", exc_info=True)
        abort(500, "Internal server error")

# Error handlers
@action.uses(db)
def handle_error(error):
    db.rollback()
    return {"error": str(error)}

# Module initialization
if __name__ == "__main__":
    # Register with router
    try:
        router_service.register_module()
        logger.info(f"{Config.MODULE_NAME} v{Config.MODULE_VERSION} started successfully")
    except Exception as e:
        logger.error(f"Failed to register module: {e}")