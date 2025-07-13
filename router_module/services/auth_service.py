"""
API Authentication service for router endpoints
Handles service account creation, API key validation, and usage tracking
"""

import hashlib
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from functools import wraps

from py4web import request, HTTP

from ..models import db

logger = logging.getLogger(__name__)

class AuthService:
    """Service for managing API authentication and service accounts"""
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return f"wbot_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def create_service_account(
        account_name: str,
        account_type: str,
        platform: str = None,
        permissions: List[str] = None,
        rate_limit: int = 1000,
        description: str = None,
        created_by: str = "system"
    ) -> Tuple[int, str]:
        """Create a new service account and return (account_id, api_key)"""
        try:
            # Generate API key
            api_key = AuthService.generate_api_key()
            api_key_hash = AuthService.hash_api_key(api_key)
            
            # Set default permissions based on account type
            if permissions is None:
                permissions = AuthService.get_default_permissions(account_type)
            
            # Create service account
            account_id = db.service_accounts.insert(
                account_name=account_name,
                account_type=account_type,
                platform=platform,
                api_key=api_key,
                api_key_hash=api_key_hash,
                permissions=permissions,
                rate_limit=rate_limit,
                description=description,
                created_by=created_by
            )
            db.commit()
            
            logger.info(f"Created service account: {account_name} ({account_type})")
            return account_id, api_key
            
        except Exception as e:
            logger.error(f"Error creating service account: {str(e)}")
            raise
    
    @staticmethod
    def get_default_permissions(account_type: str) -> List[str]:
        """Get default permissions for account type"""
        permission_sets = {
            'collector': [
                'router/events',
                'router/events/batch',
                'router/coordination/*',
                'router/responses'
            ],
            'interaction': [
                'router/responses',
                'router/commands',
                'router/entities'
            ],
            'webhook': [
                'router/responses'
            ],
            'admin': [
                'router/*',
                'admin/*'
            ]
        }
        return permission_sets.get(account_type, [])
    
    @staticmethod
    def validate_api_key(api_key: str) -> Optional[Dict]:
        """Validate API key and return service account info"""
        try:
            if not api_key or not api_key.startswith('wbot_'):
                return None
            
            # Look up service account by API key
            account = db(
                (db.service_accounts.api_key == api_key) &
                (db.service_accounts.is_active == True)
            ).select().first()
            
            if not account:
                return None
            
            # Check expiration
            if account.expires_at and account.expires_at < datetime.utcnow():
                return None
            
            # Update last used
            db.service_accounts[account.id] = dict(
                last_used=datetime.utcnow(),
                usage_count=account.usage_count + 1
            )
            db.commit()
            
            return dict(account)
            
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return None
    
    @staticmethod
    def check_permission(account: Dict, endpoint: str, method: str = 'GET') -> bool:
        """Check if service account has permission for endpoint"""
        try:
            permissions = account.get('permissions', [])
            
            # Check exact match
            full_endpoint = f"{method} {endpoint}"
            if full_endpoint in permissions:
                return True
            
            # Check endpoint without method
            if endpoint in permissions:
                return True
            
            # Check wildcard patterns
            for permission in permissions:
                if permission.endswith('/*'):
                    base_path = permission[:-2]
                    if endpoint.startswith(base_path):
                        return True
                elif permission.endswith('*'):
                    base_path = permission[:-1]
                    if endpoint.startswith(base_path):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False
    
    @staticmethod
    def check_rate_limit(account: Dict) -> bool:
        """Check if service account is within rate limits"""
        try:
            account_id = account['id']
            rate_limit = account.get('rate_limit', 1000)
            
            if rate_limit <= 0:  # No rate limit
                return True
            
            # Count requests in the last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_requests = db(
                (db.api_usage.service_account_id == account_id) &
                (db.api_usage.timestamp > one_hour_ago)
            ).count()
            
            return recent_requests < rate_limit
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False
    
    @staticmethod
    def log_api_usage(
        account: Dict,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int = None,
        request_size: int = None,
        response_size: int = None
    ):
        """Log API usage for monitoring and billing"""
        try:
            db.api_usage.insert(
                service_account_id=account['id'],
                endpoint=endpoint,
                method=method,
                ip_address=request.environ.get('REMOTE_ADDR'),
                user_agent=request.environ.get('HTTP_USER_AGENT'),
                response_status=status_code,
                response_time_ms=response_time_ms,
                request_size=request_size,
                response_size=response_size
            )
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging API usage: {str(e)}")
    
    @staticmethod
    def revoke_api_key(account_id: int) -> bool:
        """Revoke an API key by deactivating the service account"""
        try:
            db.service_accounts[account_id] = dict(
                is_active=False,
                updated_at=datetime.utcnow()
            )
            db.commit()
            
            logger.info(f"Revoked API key for service account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            return False
    
    @staticmethod
    def regenerate_api_key(account_id: int) -> Optional[str]:
        """Generate a new API key for existing service account"""
        try:
            new_api_key = AuthService.generate_api_key()
            new_api_key_hash = AuthService.hash_api_key(new_api_key)
            
            db.service_accounts[account_id] = dict(
                api_key=new_api_key,
                api_key_hash=new_api_key_hash,
                updated_at=datetime.utcnow()
            )
            db.commit()
            
            logger.info(f"Regenerated API key for service account {account_id}")
            return new_api_key
            
        except Exception as e:
            logger.error(f"Error regenerating API key: {str(e)}")
            return None
    
    @staticmethod
    def get_usage_stats(account_id: int = None, days: int = 7) -> Dict:
        """Get API usage statistics"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            if account_id:
                # Stats for specific account
                query = (db.api_usage.service_account_id == account_id) & (db.api_usage.timestamp > since_date)
            else:
                # Global stats
                query = (db.api_usage.timestamp > since_date)
            
            total_requests = db(query).count()
            
            # Group by status code
            status_stats = db(query).select(
                db.api_usage.response_status,
                db.api_usage.id.count(),
                groupby=db.api_usage.response_status
            )
            
            # Group by endpoint
            endpoint_stats = db(query).select(
                db.api_usage.endpoint,
                db.api_usage.id.count(),
                groupby=db.api_usage.endpoint,
                orderby=~db.api_usage.id.count(),
                limitby=(0, 10)
            )
            
            return {
                'total_requests': total_requests,
                'period_days': days,
                'status_codes': {
                    row.api_usage.response_status: row._extra[db.api_usage.id.count()]
                    for row in status_stats
                },
                'top_endpoints': [
                    {
                        'endpoint': row.api_usage.endpoint,
                        'requests': row._extra[db.api_usage.id.count()]
                    }
                    for row in endpoint_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {str(e)}")
            return {}

def require_api_key(allowed_account_types: List[str] = None):
    """Decorator to require API key authentication for endpoints"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Get API key from header
            api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
            
            if not api_key:
                raise HTTP(401, "API key required")
            
            # Validate API key
            account = AuthService.validate_api_key(api_key)
            if not account:
                raise HTTP(401, "Invalid API key")
            
            # Check account type if specified
            if allowed_account_types and account['account_type'] not in allowed_account_types:
                raise HTTP(403, f"Account type '{account['account_type']}' not allowed for this endpoint")
            
            # Check permissions
            endpoint = request.environ.get('PATH_INFO', '').replace('/router/', 'router/')
            method = request.environ.get('REQUEST_METHOD', 'GET')
            
            if not AuthService.check_permission(account, endpoint, method):
                raise HTTP(403, "Insufficient permissions")
            
            # Check rate limits
            if not AuthService.check_rate_limit(account):
                raise HTTP(429, "Rate limit exceeded")
            
            # Add account to request context
            request.auth_account = account
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Log successful usage
                response_time = int((time.time() - start_time) * 1000)
                AuthService.log_api_usage(
                    account=account,
                    endpoint=endpoint,
                    method=method,
                    status_code=200,
                    response_time_ms=response_time
                )
                
                return result
                
            except HTTP as e:
                # Log failed usage
                response_time = int((time.time() - start_time) * 1000)
                AuthService.log_api_usage(
                    account=account,
                    endpoint=endpoint,
                    method=method,
                    status_code=e.status,
                    response_time_ms=response_time
                )
                raise
                
        return wrapper
    return decorator

# Global auth service instance
auth_service = AuthService()