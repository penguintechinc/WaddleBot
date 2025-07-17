"""
Router Service for YouTube Music Module
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
                'module_type': 'interaction',
                'commands': [
                    {
                        'command': '!ytmusic',
                        'description': 'YouTube Music search and playback',
                        'trigger_type': 'command',
                        'location': 'internal',
                        'type': 'container'
                    },
                    {
                        'command': '!youtube',
                        'description': 'YouTube Music alias',
                        'trigger_type': 'command',
                        'location': 'internal',
                        'type': 'container'
                    }
                ],
                'health_endpoint': f"http://{self.module_name}:{self.config.MODULE_PORT}/youtube/music/health",
                'interaction_endpoint': f"http://{self.module_name}:{self.config.MODULE_PORT}/youtube/music/interaction"
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
    
    def send_response(self, response_data: Dict) -> bool:
        """Send response back to router"""
        try:
            # Ensure we have module name in response
            response_data['module_name'] = self.module_name
            
            response = self.session.post(
                f"{self.router_url}/responses",
                json=response_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"AUDIT module={self.module_name} action=send_response session_id={response_data.get('session_id')} status=SUCCESS")
                return True
            else:
                logger.error(f"ERROR module={self.module_name} action=send_response status_code={response.status_code} response={response.text}")
                return False
                
        except Exception as e:
            logger.error(f"ERROR module={self.module_name} action=send_response error={str(e)}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to router"""
        try:
            data = {
                'module_name': self.module_name,
                'module_version': self.module_version,
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
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
    
    def get_entity_config(self, entity_id: str) -> Optional[Dict]:
        """Get entity configuration from router"""
        try:
            response = self.session.get(
                f"{self.router_url}/entities/{entity_id}/config",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            logger.error(f"ERROR module={self.module_name} action=get_entity_config entity_id={entity_id} error={str(e)}")
            return None
    
    def check_user_permission(self, entity_id: str, user_id: str, permission: str) -> bool:
        """Check if user has permission for action"""
        try:
            data = {
                'entity_id': entity_id,
                'user_id': user_id,
                'permission': permission
            }
            
            response = self.session.post(
                f"{self.router_url}/permissions/check",
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('has_permission', False)
            else:
                return False
                
        except Exception as e:
            logger.error(f"ERROR module={self.module_name} action=check_permission error={str(e)}")
            return False