"""
RBAC middleware for permission checking in router
"""

import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
from py4web import request, response, HTTP

from ..services.rbac_service import rbac_service
from ..models import GLOBAL_COMMUNITY_ID

logger = logging.getLogger(__name__)

class RBACMiddleware:
    """Middleware for role-based access control"""
    
    def __init__(self):
        self.rbac_service = rbac_service
    
    def require_permission(self, permission: str, entity_id_key: str = "entity_id", 
                          community_id_key: str = "community_id"):
        """Decorator to require specific permission for endpoint access"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Get user_id from request - assume it's set by auth middleware
                    user_id = getattr(request, 'user_id', None)
                    if not user_id:
                        raise HTTP(401, "User not authenticated")
                    
                    # Get entity_id and community_id from request data
                    request_data = request.json or {}
                    entity_id = request_data.get(entity_id_key)
                    community_id = request_data.get(community_id_key)
                    
                    # Check permission
                    has_permission = self.rbac_service.has_permission(
                        user_id=user_id,
                        permission=permission,
                        entity_id=entity_id,
                        community_id=community_id
                    )
                    
                    if not has_permission:
                        raise HTTP(403, f"Permission denied: {permission}")
                    
                    return func(*args, **kwargs)
                    
                except HTTP:
                    raise
                except Exception as e:
                    logger.error(f"Error in RBAC middleware: {str(e)}")
                    raise HTTP(500, "Internal server error")
            
            return wrapper
        return decorator
    
    def require_role(self, role: str, entity_id_key: str = "entity_id", 
                    community_id_key: str = "community_id"):
        """Decorator to require specific role level for endpoint access"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Get user_id from request - assume it's set by auth middleware
                    user_id = getattr(request, 'user_id', None)
                    if not user_id:
                        raise HTTP(401, "User not authenticated")
                    
                    # Get entity_id and community_id from request data
                    request_data = request.json or {}
                    entity_id = request_data.get(entity_id_key)
                    community_id = request_data.get(community_id_key)
                    
                    # Check role level
                    has_role = self.rbac_service.has_role_level(
                        user_id=user_id,
                        required_role=role,
                        entity_id=entity_id,
                        community_id=community_id
                    )
                    
                    if not has_role:
                        raise HTTP(403, f"Role required: {role}")
                    
                    return func(*args, **kwargs)
                    
                except HTTP:
                    raise
                except Exception as e:
                    logger.error(f"Error in RBAC middleware: {str(e)}")
                    raise HTTP(500, "Internal server error")
            
            return wrapper
        return decorator
    
    def ensure_global_community_access(self, func: Callable) -> Callable:
        """Decorator to ensure user has global community access"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Get user_id from request - assume it's set by auth middleware
                user_id = getattr(request, 'user_id', None)
                if not user_id:
                    raise HTTP(401, "User not authenticated")
                
                # Ensure user has access to global community
                self.rbac_service.ensure_user_in_global_community(user_id)
                
                return func(*args, **kwargs)
                
            except HTTP:
                raise
            except Exception as e:
                logger.error(f"Error ensuring global community access: {str(e)}")
                raise HTTP(500, "Internal server error")
        
        return wrapper
    
    def check_command_permission(self, user_id: str, command_name: str, 
                               entity_id: str = None, community_id: int = None) -> bool:
        """Check if user has permission to execute a specific command"""
        try:
            # Define command to permission mapping
            command_permissions = {
                # Community management commands
                "community": "commands.basic",
                "create_community": "community.add_entity",
                "manage_community": "community.manage_settings",
                "add_user": "community.add_user",
                "remove_user": "community.remove_user",
                "install_module": "community.install_modules",
                
                # Moderation commands
                "ban": "users.ban",
                "kick": "users.kick",
                "timeout": "users.timeout",
                "warn": "users.warn",
                
                # Admin commands
                "config": "commands.admin",
                "settings": "commands.admin",
                
                # Basic commands
                "help": "commands.basic",
                "info": "commands.basic",
                "stats": "commands.basic"
            }
            
            required_permission = command_permissions.get(command_name, "commands.basic")
            
            return self.rbac_service.has_permission(
                user_id=user_id,
                permission=required_permission,
                entity_id=entity_id,
                community_id=community_id
            )
            
        except Exception as e:
            logger.error(f"Error checking command permission: {str(e)}")
            return False
    
    def get_user_permissions(self, user_id: str, entity_id: str = None, 
                           community_id: int = None) -> Dict[str, Any]:
        """Get user's permissions and role information"""
        try:
            # Get user's role
            if entity_id:
                user_role = self.rbac_service.get_user_role_for_entity(user_id, entity_id)
            elif community_id:
                user_role = self.rbac_service.get_user_role_in_community(user_id, community_id)
            else:
                user_role = self.rbac_service.get_user_role_in_community(user_id, GLOBAL_COMMUNITY_ID)
            
            # Get user's permissions
            permissions = self.rbac_service.get_user_permissions(user_id, entity_id, community_id)
            
            return {
                "user_id": user_id,
                "role": user_role,
                "permissions": permissions,
                "entity_id": entity_id,
                "community_id": community_id
            }
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return {
                "user_id": user_id,
                "role": None,
                "permissions": [],
                "entity_id": entity_id,
                "community_id": community_id
            }

# Global middleware instance
rbac_middleware = RBACMiddleware()

# Convenience decorators
require_permission = rbac_middleware.require_permission
require_role = rbac_middleware.require_role
ensure_global_community_access = rbac_middleware.ensure_global_community_access