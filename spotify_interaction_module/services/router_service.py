"""
Router Service for Spotify Module
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
                        'command': '!spotify',
                        'description': 'Spotify music search and playback control',
                        'trigger_type': 'command',
                        'location': 'internal',
                        'type': 'container'
                    },
                    {
                        'command': '!spot',
                        'description': 'Spotify music alias',
                        'trigger_type': 'command',
                        'location': 'internal',
                        'type': 'container'
                    }
                ],
                'health_endpoint': f"http://{self.module_name}:{self.config.MODULE_PORT}/spotify/health",
                'interaction_endpoint': f"http://{self.module_name}:{self.config.MODULE_PORT}/spotify/interaction"
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