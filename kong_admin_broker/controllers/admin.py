#!/usr/bin/env python3
"""
Kong Admin Broker API Controller
Manages Kong super admin users and provides API endpoints for user management
"""

import logging
import time
import traceback
from py4web import action, request, response, HTTP
from py4web.core import Fixture
import json
from typing import Dict, Any, Optional

from config import Config
from services.user_manager import SuperAdminUserManager
from services.kong_client import KongAdminClient

# Configure logging
logger = logging.getLogger(__name__)

# Initialize services
user_manager = SuperAdminUserManager()
kong_client = KongAdminClient()

class BrokerAuthFixture(Fixture):
    """Broker API authentication fixture"""
    
    def on_request(self, context):
        # Check for broker API key
        api_key = request.headers.get('X-Broker-Key') or request.query.get('broker_key')
        
        if not api_key:
            raise HTTP(401, "Broker API key required")
        
        if api_key != Config.BROKER_API_KEY:
            raise HTTP(403, "Invalid broker API key")
        
        # Extract client information
        context['broker_authenticated'] = True
        context['client_ip'] = request.headers.get('X-Forwarded-For', request.environ.get('REMOTE_ADDR', ''))
        context['user_agent'] = request.headers.get('User-Agent', '')

broker_auth = BrokerAuthFixture()

@action('api/v1/health', method=['GET'])
def health():
    """
    Broker health check endpoint (no auth required)
    """
    try:
        kong_health = kong_client.health_check()
        
        return {
            "status": "healthy" if kong_health else "unhealthy",
            "kong_admin": "connected" if kong_health else "disconnected",
            "service": "kong_admin_broker",
            "version": Config.MODULE_VERSION,
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Broker health check failed: {str(e)}")
        response.status = 503
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "kong_admin_broker",
            "timestamp": int(time.time())
        }

@action('api/v1/super-admins', method=['POST'])
@action.uses(broker_auth)
def create_super_admin():
    """
    Create a new Kong super admin user
    """
    try:
        data = request.json
        if not data:
            raise HTTP(400, "Request body is required")
        
        # Extract required fields
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        full_name = data.get('full_name', '').strip()
        created_by = data.get('created_by', 'broker').strip()
        
        # Optional fields
        permissions = data.get('permissions')
        notes = data.get('notes')
        
        # Validation
        if not username:
            raise HTTP(400, "Username is required")
        
        if not email:
            raise HTTP(400, "Email is required")
        
        if not full_name:
            raise HTTP(400, "Full name is required")
        
        # Validate email format (basic check)
        if '@' not in email or '.' not in email:
            raise HTTP(400, "Invalid email format")
        
        # Create super admin user
        result = user_manager.create_super_admin(
            username=username,
            email=email,
            full_name=full_name,
            created_by=created_by,
            permissions=permissions,
            notes=notes
        )
        
        # Remove sensitive API key from response log
        safe_result = result.copy()
        if 'api_key' in safe_result:
            safe_result['api_key'] = '***REDACTED***'
        
        logger.info(f"Created super admin user via broker: {username}")
        
        return result
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in create super admin: {str(e)}\n{traceback.format_exc()}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/super-admins/<username>', method=['GET'])
@action.uses(broker_auth)
def get_super_admin(username):
    """
    Get super admin user by username
    """
    try:
        user = user_manager.get_super_admin(username)
        
        if not user:
            raise HTTP(404, f"Super admin user '{username}' not found")
        
        # Remove sensitive API key from response
        if 'api_key' in user:
            user['api_key'] = '***REDACTED***'
        
        return user
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error getting super admin {username}: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/super-admins', method=['GET'])
@action.uses(broker_auth)
def list_super_admins():
    """
    List all super admin users
    """
    try:
        include_inactive = request.query.get('include_inactive', 'false').lower() == 'true'
        
        users = user_manager.list_super_admins(include_inactive=include_inactive)
        
        return {
            "super_admins": users,
            "total_count": len(users),
            "include_inactive": include_inactive
        }
        
    except Exception as e:
        logger.error(f"Error listing super admins: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/super-admins/<username>', method=['PUT'])
@action.uses(broker_auth)
def update_super_admin(username):
    """
    Update super admin user
    """
    try:
        data = request.json
        if not data:
            raise HTTP(400, "Request body is required")
        
        updated_by = data.get('updated_by', 'broker')
        
        # Remove non-updatable fields
        updates = data.copy()
        updates.pop('updated_by', None)
        updates.pop('username', None)  # Username cannot be updated
        updates.pop('kong_consumer_id', None)  # Kong consumer ID cannot be updated
        updates.pop('api_key', None)  # API key has separate endpoint
        
        result = user_manager.update_super_admin(
            username=username,
            updates=updates,
            updated_by=updated_by
        )
        
        return result
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error updating super admin {username}: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/super-admins/<username>/deactivate', method=['POST'])
@action.uses(broker_auth)
def deactivate_super_admin(username):
    """
    Deactivate super admin user
    """
    try:
        data = request.json or {}
        
        deactivated_by = data.get('deactivated_by', 'broker')
        reason = data.get('reason', 'Deactivated via broker API')
        
        result = user_manager.deactivate_super_admin(
            username=username,
            deactivated_by=deactivated_by,
            reason=reason
        )
        
        return result
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error deactivating super admin {username}: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/super-admins/<username>/regenerate-key', method=['POST'])
@action.uses(broker_auth)
def regenerate_api_key(username):
    """
    Regenerate API key for super admin user
    """
    try:
        data = request.json or {}
        regenerated_by = data.get('regenerated_by', 'broker')
        
        result = user_manager.regenerate_api_key(
            username=username,
            regenerated_by=regenerated_by
        )
        
        return result
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error regenerating API key for {username}: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/audit-log', method=['GET'])
@action.uses(broker_auth)
def get_audit_log():
    """
    Get audit log entries
    """
    try:
        # Query parameters
        username = request.query.get('username')
        action = request.query.get('action')
        limit = int(request.query.get('limit', '100'))
        offset = int(request.query.get('offset', '0'))
        
        # Validate parameters
        if limit > 1000:
            limit = 1000
        
        if offset < 0:
            offset = 0
        
        logs = user_manager.get_audit_log(
            username=username,
            action=action,
            limit=limit,
            offset=offset
        )
        
        return {
            "audit_logs": logs,
            "count": len(logs),
            "limit": limit,
            "offset": offset,
            "filters": {
                "username": username,
                "action": action
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting audit log: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/backup', method=['POST'])
@action.uses(broker_auth)
def backup_super_admins():
    """
    Create backup of all super admin users
    """
    try:
        data = request.json or {}
        
        backup_type = data.get('backup_type', 'manual')
        created_by = data.get('created_by', 'broker')
        
        result = user_manager.backup_all_super_admins(
            backup_type=backup_type,
            created_by=created_by
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error backing up super admins: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/kong/info', method=['GET'])
@action.uses(broker_auth)
def get_kong_info():
    """
    Get Kong server information
    """
    try:
        kong_info = kong_client.get_kong_info()
        
        return {
            "kong_info": kong_info,
            "admin_url": Config.KONG_ADMIN_URL,
            "broker_version": Config.MODULE_VERSION
        }
        
    except Exception as e:
        logger.error(f"Error getting Kong info: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/kong/consumers', method=['GET'])
@action.uses(broker_auth)
def list_kong_consumers():
    """
    List all Kong consumers with pagination
    """
    try:
        size = int(request.query.get('size', '100'))
        offset = request.query.get('offset')
        
        if size > 1000:
            size = 1000
        
        consumers = kong_client.list_all_consumers(size=size, offset=offset)
        
        return consumers
        
    except Exception as e:
        logger.error(f"Error listing Kong consumers: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/kong/consumers/<username>/backup', method=['POST'])
@action.uses(broker_auth)
def backup_kong_consumer(username):
    """
    Create backup of specific Kong consumer
    """
    try:
        backup_data = kong_client.backup_consumer(username)
        
        return {
            "success": True,
            "username": username,
            "backup_data": backup_data,
            "message": f"Backup created for consumer '{username}'"
        }
        
    except Exception as e:
        logger.error(f"Error backing up Kong consumer {username}: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/statistics', method=['GET'])
@action.uses(broker_auth)
def get_statistics():
    """
    Get broker and Kong statistics
    """
    try:
        # Get super admin statistics
        active_admins = user_manager.list_super_admins(include_inactive=False)
        inactive_admins = user_manager.list_super_admins(include_inactive=True)
        inactive_count = len(inactive_admins) - len(active_admins)
        
        # Get recent audit log entries
        recent_logs = user_manager.get_audit_log(limit=10)
        
        # Get Kong consumer count
        try:
            kong_consumers = kong_client.list_all_consumers(size=1)
            total_consumers = kong_consumers.get('total', 0)
        except:
            total_consumers = 0
        
        return {
            "super_admins": {
                "active_count": len(active_admins),
                "inactive_count": inactive_count,
                "total_count": len(inactive_admins)
            },
            "kong": {
                "total_consumers": total_consumers,
                "admin_url": Config.KONG_ADMIN_URL,
                "health": kong_client.health_check()
            },
            "recent_activity": {
                "audit_log_entries": len(recent_logs),
                "last_activity": recent_logs[0]['created_at'] if recent_logs else None
            },
            "broker": {
                "version": Config.MODULE_VERSION,
                "uptime_check": "healthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('index')
def index():
    """
    Broker service information page
    """
    return {
        "service": "Kong Admin Broker",
        "version": Config.MODULE_VERSION,
        "description": "WaddleBot Kong Admin User Management Service",
        "endpoints": {
            "health": "/api/v1/health",
            "super_admins": "/api/v1/super-admins",
            "audit_log": "/api/v1/audit-log",
            "backup": "/api/v1/backup",
            "kong_info": "/api/v1/kong/info",
            "statistics": "/api/v1/statistics"
        },
        "authentication": "X-Broker-Key header required",
        "documentation": "See API.md for detailed documentation"
    }