"""
Twitch OAuth authentication handlers
Handles user authentication flow and token management
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode
from py4web import action, request, response, HTTP, redirect, URL, Session

from ..models import db
from ..config import load_config
from ..dataclasses import TwitchToken, dataclass_to_dict
from .api import twitch_api

# Load configuration  
twitch_config, waddlebot_config = load_config()

logger = logging.getLogger(__name__)

# Session management
session = Session(secret="your-secret-key-here")

@action("twitch/auth/login")
def login():
    """Initiate Twitch OAuth flow"""
    try:
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        session["oauth_state"] = state
        
        # Optional: store gateway activation key if provided
        activation_key = request.query.get("activation_key")
        if activation_key:
            session["activation_key"] = activation_key
        
        # Build authorization URL
        auth_params = {
            "client_id": twitch_config.app_id,
            "redirect_uri": twitch_config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(twitch_config.required_scopes),
            "state": state,
            "force_verify": "true"  # Force user to re-authorize
        }
        
        auth_url = f"{twitch_config.auth_base_url}/authorize?{urlencode(auth_params)}"
        
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating login: {str(e)}")
        raise HTTP(500, f"Authentication error: {str(e)}")

@action("twitch/auth/callback")
def auth_callback():
    """Handle OAuth callback from Twitch"""
    try:
        # Get authorization code and state
        code = request.query.get("code")
        state = request.query.get("state")
        error = request.query.get("error")
        
        # Check for errors
        if error:
            logger.error(f"OAuth error: {error}")
            return {"error": f"Authentication failed: {error}"}
        
        # Verify state parameter
        if not state or state != session.get("oauth_state"):
            logger.error("Invalid state parameter")
            raise HTTP(400, "Invalid state parameter")
        
        # Clear state from session
        session.pop("oauth_state", None)
        
        if not code:
            raise HTTP(400, "Missing authorization code")
        
        # Exchange code for tokens
        token = exchange_code_for_tokens(code)
        
        # Get user information
        user_info = twitch_api.get_user_info(token.access_token)
        if not user_info:
            raise HTTP(400, "Failed to get user information")
        
        # Store tokens in database
        store_user_tokens(user_info.id, token)
        
        # Handle gateway activation if activation key was provided
        activation_key = session.pop("activation_key", None)
        if activation_key:
            from .api import waddlebot_api
            result = waddlebot_api.activate_gateway(activation_key)
            if "error" in result:
                return {"error": "Authentication successful but gateway activation failed", "user": user_info.display_name}
        
        return {
            "success": True,
            "user": dataclass_to_dict(user_info),
            "message": "Authentication successful"
        }
        
    except Exception as e:
        logger.error(f"Error in auth callback: {str(e)}")
        raise HTTP(500, f"Authentication error: {str(e)}")

def exchange_code_for_tokens(code: str) -> TwitchToken:
    """Exchange authorization code for access tokens"""
    import requests
    
    token_url = f"{twitch_config.auth_base_url}/token"
    data = {
        "client_id": twitch_config.app_id,
        "client_secret": twitch_config.app_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": twitch_config.redirect_uri
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    
    token_data = response.json()
    return TwitchToken(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_in=token_data["expires_in"],
        scope=token_data["scope"],
        token_type=token_data.get("token_type", "bearer")
    )

def store_user_tokens(user_id: str, token: TwitchToken):
    """Store user tokens in database"""
    expires_at = datetime.utcnow() + timedelta(seconds=token.expires_in)
    
    # Check if user already exists
    existing = db(db.twitch_tokens.user_id == user_id).select().first()
    
    if existing:
        # Update existing tokens
        db.twitch_tokens[existing.id] = dict(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=expires_at,
            scopes=token.scope
        )
    else:
        # Insert new tokens
        db.twitch_tokens.insert(
            user_id=user_id,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=expires_at,
            scopes=token.scope
        )
    
    db.commit()

@action("twitch/auth/refresh/<user_id>")
def refresh_user_token(user_id: str):
    """Refresh user's access token"""
    try:
        # Get current tokens
        token_record = db(db.twitch_tokens.user_id == user_id).select().first()
        if not token_record:
            raise HTTP(404, "User tokens not found")
        
        # Refresh the token
        new_token = twitch_api.refresh_token(token_record.refresh_token)
        
        # Update database
        expires_at = datetime.utcnow() + timedelta(seconds=new_token.expires_in)
        db.twitch_tokens[token_record.id] = dict(
            access_token=new_token.access_token,
            refresh_token=new_token.refresh_token,
            expires_at=expires_at,
            scopes=new_token.scope
        )
        db.commit()
        
        return {"success": True, "expires_at": expires_at.isoformat()}
        
    except Exception as e:
        logger.error(f"Error refreshing token for user {user_id}: {str(e)}")
        raise HTTP(500, f"Token refresh error: {str(e)}")

@action("twitch/auth/validate/<user_id>")
def validate_user_token(user_id: str):
    """Validate user's access token"""
    try:
        token_record = db(db.twitch_tokens.user_id == user_id).select().first()
        if not token_record:
            return {"valid": False, "reason": "No tokens found"}
        
        # Check if token has expired
        if datetime.utcnow() >= token_record.expires_at:
            return {"valid": False, "reason": "Token expired"}
        
        # Validate with Twitch API
        import requests
        headers = {
            "Authorization": f"OAuth {token_record.access_token}"
        }
        
        response = requests.get("https://id.twitch.tv/oauth2/validate", headers=headers)
        
        if response.status_code == 200:
            token_info = response.json()
            return {
                "valid": True,
                "client_id": token_info.get("client_id"),
                "scopes": token_info.get("scopes"),
                "expires_in": token_info.get("expires_in")
            }
        else:
            return {"valid": False, "reason": "Token validation failed"}
            
    except Exception as e:
        logger.error(f"Error validating token for user {user_id}: {str(e)}")
        return {"valid": False, "reason": str(e)}

@action("twitch/auth/revoke/<user_id>")
def revoke_user_token(user_id: str):
    """Revoke user's access token"""
    try:
        token_record = db(db.twitch_tokens.user_id == user_id).select().first()
        if not token_record:
            raise HTTP(404, "User tokens not found")
        
        # Revoke token with Twitch
        import requests
        revoke_url = f"{twitch_config.auth_base_url}/revoke"
        data = {
            "client_id": twitch_config.app_id,
            "token": token_record.access_token
        }
        
        response = requests.post(revoke_url, data=data)
        
        # Remove from database regardless of Twitch API response
        db(db.twitch_tokens.user_id == user_id).delete()
        db.commit()
        
        return {"success": True, "message": "Token revoked"}
        
    except Exception as e:
        logger.error(f"Error revoking token for user {user_id}: {str(e)}")
        raise HTTP(500, f"Token revocation error: {str(e)}")

@action("twitch/auth/status")
def auth_status():
    """Check authentication status"""
    try:
        user_id = request.query.get("user_id")
        if not user_id:
            return {"authenticated": False, "reason": "No user ID provided"}
        
        validation_result = validate_user_token(user_id)
        return {
            "authenticated": validation_result.get("valid", False),
            "user_id": user_id,
            "details": validation_result
        }
        
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
        return {"authenticated": False, "reason": str(e)}

@action("twitch/auth/users")
def list_authenticated_users():
    """List all authenticated users"""
    try:
        # Get all valid tokens (not expired)
        current_time = datetime.utcnow()
        valid_tokens = db(db.twitch_tokens.expires_at > current_time).select()
        
        users = []
        for token in valid_tokens:
            try:
                # Get user info for each valid token
                user_info = twitch_api.get_user_info(token.access_token)
                if user_info:
                    users.append({
                        "user_id": token.user_id,
                        "display_name": user_info.display_name,
                        "login": user_info.login,
                        "expires_at": token.expires_at.isoformat(),
                        "scopes": token.scopes
                    })
            except Exception as e:
                logger.warning(f"Error getting info for user {token.user_id}: {str(e)}")
        
        return {"users": users}
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTP(500, f"Error: {str(e)}")

def get_valid_token(user_id: str) -> str:
    """Get valid access token for user, refreshing if necessary"""
    token_record = db(db.twitch_tokens.user_id == user_id).select().first()
    if not token_record:
        raise ValueError("No tokens found for user")
    
    # Check if token needs refresh
    if datetime.utcnow() >= token_record.expires_at - timedelta(minutes=5):
        # Token expires soon, refresh it
        new_token = twitch_api.refresh_token(token_record.refresh_token)
        
        expires_at = datetime.utcnow() + timedelta(seconds=new_token.expires_in)
        db.twitch_tokens[token_record.id] = dict(
            access_token=new_token.access_token,
            refresh_token=new_token.refresh_token,
            expires_at=expires_at
        )
        db.commit()
        
        return new_token.access_token
    
    return token_record.access_token