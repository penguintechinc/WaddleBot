"""
Router Service for Browser Source Module
Handles communication with the WaddleBot router
"""

import logging
import requests
import json
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class RouterService:
    """Service for communicating with WaddleBot router"""
    
    def __init__(self, config):
        self.config = config
        self.router_url = config.ROUTER_API_URL
        self.api_key = config.API_KEY
        self.module_name = config.MODULE_NAME
        self.module_version = config.MODULE_VERSION
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def register_module(self) -> bool:
        """Register module with router"""
        try:
            data = {
                'module_name': self.module_name,
                'module_version': self.module_version,
                'module_type': 'core',
                'endpoints': [
                    {
                        'path': '/browser/source/display',
                        'method': 'POST',
                        'description': 'Receive display data from router',
                        'auth_required': True
                    },
                    {
                        'path': '/browser/source/admin/tokens',
                        'method': ['GET', 'POST'],
                        'description': 'Manage browser source tokens',
                        'auth_required': True
                    },
                    {
                        'path': '/browser/source/api/communities/{community_id}/urls',
                        'method': 'GET',
                        'description': 'Get community browser source URLs',
                        'auth_required': True
                    }
                ],
                'health_endpoint': f"http://{self.module_name}:{self.config.MODULE_PORT}/browser/source/health",
                'display_endpoint': f"http://{self.module_name}:{self.config.MODULE_PORT}/browser/source/display"
            }
            
            response = self.session.post(
                f"{self.router_url}/modules/register",
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"SYSTEM module={self.module_name} event=registered status=SUCCESS")
                return True
            else:
                logger.error(f"SYSTEM module={self.module_name} event=register_failed status_code={response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"ERROR module={self.module_name} action=register error={str(e)}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to router"""
        try:
            data = {
                'module_name': self.module_name,
                'module_version': self.module_version,
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'active_connections': self._get_connection_count()
            }
            
            response = self.session.post(
                f"{self.router_url}/modules/heartbeat",
                json=data,
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"ERROR module={self.module_name} action=heartbeat error={str(e)}")
            return False
    
    def _get_connection_count(self) -> int:
        """Get current connection count for heartbeat"""
        try:
            # This would be provided by the browser service
            return 0
        except:
            return 0
    
    def register_browser_source_route(self, community_id: str, source_type: str, token: str) -> bool:
        """Register a browser source route with the router"""
        try:
            data = {
                'community_id': community_id,
                'source_type': source_type,
                'token': token,
                'url': f"{self.config.BASE_URL}/browser/source/{token}/{source_type}",
                'module_name': self.module_name
            }
            
            response = self.session.post(
                f"{self.router_url}/browser-sources/register",
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Registered browser source route for {community_id}/{source_type}")
                return True
            else:
                logger.error(f"Failed to register browser source route: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Browser source route registration failed: {str(e)}")
            return False
    
    def get_community_permissions(self, community_id: str, user_id: str) -> Dict:
        """Get community permissions for user"""
        try:
            params = {
                'community_id': community_id,
                'user_id': user_id
            }
            
            response = self.session.get(
                f"{self.router_url}/permissions/community",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get community permissions: {str(e)}")
            return {}
    
    def validate_community_access(self, community_id: str, user_id: str) -> bool:
        """Validate if user has access to community browser sources"""
        try:
            permissions = self.get_community_permissions(community_id, user_id)
            return permissions.get('can_manage_browser_sources', False)
            
        except Exception as e:
            logger.error(f"Community access validation failed: {str(e)}")
            return False
    
    def log_browser_source_activity(self, community_id: str, source_type: str, action: str, user_id: str = None) -> bool:
        """Log browser source activity to router"""
        try:
            data = {
                'module_name': self.module_name,
                'community_id': community_id,
                'source_type': source_type,
                'action': action,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = self.session.post(
                f"{self.router_url}/activity/log",
                json=data,
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Activity logging failed: {str(e)}")
            return False
    
    def get_router_config(self) -> Dict:
        """Get router configuration"""
        try:
            response = self.session.get(
                f"{self.router_url}/config",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get router config: {str(e)}")
            return {}
    
    def notify_router_display_update(self, community_id: str, source_type: str, update_type: str) -> bool:
        """Notify router of display update"""
        try:
            data = {
                'community_id': community_id,
                'source_type': source_type,
                'update_type': update_type,
                'module_name': self.module_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = self.session.post(
                f"{self.router_url}/browser-sources/update",
                json=data,
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Display update notification failed: {str(e)}")
            return False