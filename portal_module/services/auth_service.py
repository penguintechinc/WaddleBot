"""
Authentication service for the portal
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from functools import wraps

from py4web import request, response, HTTP, redirect, URL

logger = logging.getLogger(__name__)

class PortalAuthService:
    """Authentication service for portal access"""
    
    def __init__(self, db):
        self.db = db
    
    def generate_temp_password(self) -> str:
        """Generate a temporary password"""
        return secrets.token_urlsafe(12)
    
    def hash_password(self, password: str) -> str:
        """Hash a password for storage"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_portal_user(self, user_id: str, email: str, display_name: str = None) -> Dict[str, Any]:
        """Create a new portal user with temporary password"""
        try:
            # Check if user already exists
            existing_user = self.db(self.db.portal_users.user_id == user_id).select().first()
            
            if existing_user:
                return {"success": False, "error": "User already exists"}
            
            # Generate temporary password
            temp_password = self.generate_temp_password()
            temp_password_hash = self.hash_password(temp_password)
            
            # Create user
            user_id_db = self.db.portal_users.insert(
                user_id=user_id,
                email=email,
                display_name=display_name or user_id,
                temp_password=temp_password_hash,
                temp_password_expires=datetime.utcnow() + timedelta(hours=24),
                is_active=True
            )
            
            self.db.commit()
            
            return {
                "success": True,
                "user_id": user_id,
                "temp_password": temp_password,
                "expires_at": datetime.utcnow() + timedelta(hours=24)
            }
            
        except Exception as e:
            logger.error(f"Error creating portal user: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def authenticate_user(self, user_id: str, password: str) -> Dict[str, Any]:
        """Authenticate user with password"""
        try:
            # Get user
            user = self.db(
                (self.db.portal_users.user_id == user_id) &
                (self.db.portal_users.is_active == True)
            ).select().first()
            
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if temp password is still valid
            if user.temp_password_expires and user.temp_password_expires < datetime.utcnow():
                return {"success": False, "error": "Temporary password expired"}
            
            # Verify password
            password_hash = self.hash_password(password)
            if user.temp_password != password_hash:
                return {"success": False, "error": "Invalid password"}
            
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            session_expires = datetime.utcnow() + timedelta(hours=8)
            
            # Create session
            self.db.portal_sessions.insert(
                user_id=user_id,
                session_token=session_token,
                expires_at=session_expires
            )
            
            # Update last login
            self.db(self.db.portal_users.id == user.id).update(
                last_login=datetime.utcnow()
            )
            
            self.db.commit()
            
            return {
                "success": True,
                "session_token": session_token,
                "expires_at": session_expires,
                "user": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "display_name": user.display_name
                }
            }
            
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate a session token"""
        try:
            if not session_token:
                return None
            
            # Get session
            session = self.db(
                (self.db.portal_sessions.session_token == session_token) &
                (self.db.portal_sessions.expires_at > datetime.utcnow())
            ).select().first()
            
            if not session:
                return None
            
            # Get user
            user = self.db(
                (self.db.portal_users.user_id == session.user_id) &
                (self.db.portal_users.is_active == True)
            ).select().first()
            
            if not user:
                return None
            
            return {
                "user_id": user.user_id,
                "email": user.email,
                "display_name": user.display_name,
                "session_expires": session.expires_at
            }
            
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return None
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user by invalidating session"""
        try:
            if not session_token:
                return False
            
            # Delete session
            self.db(self.db.portal_sessions.session_token == session_token).delete()
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging out user: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            # Delete expired sessions
            count = self.db(
                self.db.portal_sessions.expires_at < datetime.utcnow()
            ).delete()
            
            # Delete expired temp passwords
            self.db(
                (self.db.portal_users.temp_password_expires < datetime.utcnow()) &
                (self.db.portal_users.temp_password_expires.isnot(None))
            ).update(
                temp_password=None,
                temp_password_expires=None
            )
            
            self.db.commit()
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
            return 0

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Get session token from cookie or header
        session_token = request.cookies.get('session_token') or request.headers.get('X-Session-Token')
        
        if not session_token:
            if request.path.startswith('/api/'):
                raise HTTP(401, "Authentication required")
            else:
                redirect(URL('login'))
        
        # Validate session
        from ..app import db
        auth_service = PortalAuthService(db)
        user = auth_service.validate_session(session_token)
        
        if not user:
            if request.path.startswith('/api/'):
                raise HTTP(401, "Invalid or expired session")
            else:
                redirect(URL('login'))
        
        # Add user to request
        request.user = user
        
        return f(*args, **kwargs)
    
    return wrapper