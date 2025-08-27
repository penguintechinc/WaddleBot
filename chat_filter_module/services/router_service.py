"""
Router Service for Chat Filter Module
Handles communication with the core router
"""

import json
import logging
import requests
from typing import Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class RouterService:
    """Service for communicating with the WaddleBot router"""
    
    def __init__(self):
        self.router_url = Config.ROUTER_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': f'{Config.MODULE_NAME}/{Config.MODULE_VERSION}'
        })
    
    def register_module(self) -> bool:
        """Register this module with the router"""
        try:
            registration_data = {
                'module_name': Config.MODULE_NAME,
                'module_version': Config.MODULE_VERSION,
                'module_type': 'filter',
                'endpoint_url': f'http://chat-filter:{Config.MODULE_PORT}',
                'capabilities': [
                    'profanity_filtering',
                    'spam_detection',
                    'url_blocking'
                ],
                'health_check_url': f'http://chat-filter:{Config.MODULE_PORT}/health'
            }
            
            response = self.session.post(
                f"{self.router_url}/modules/register",
                json=registration_data,
                timeout=Config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                logger.info("Successfully registered with router")
                return True
            else:
                logger.error(f"Failed to register with router: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering with router: {str(e)}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to router"""
        try:
            heartbeat_data = {
                'module_name': Config.MODULE_NAME,
                'status': 'healthy',
                'timestamp': Config.MODULE_VERSION,
                'stats': {
                    'messages_processed': 0,  # TODO: Implement actual stats
                    'violations_found': 0,
                    'uptime_seconds': 0
                }
            }
            
            response = self.session.post(
                f"{self.router_url}/modules/heartbeat",
                json=heartbeat_data,
                timeout=Config.REQUEST_TIMEOUT
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending heartbeat: {str(e)}")
            return False
    
    def report_violation(self, community_id: str, user_id: str, violation_data: Dict[str, Any]) -> bool:
        """Report a filter violation to the router"""
        try:
            report_data = {
                'module_name': Config.MODULE_NAME,
                'community_id': community_id,
                'user_id': user_id,
                'violation_type': 'chat_filter',
                'violation_data': violation_data,
                'severity': violation_data.get('severity', 'moderate'),
                'action_taken': violation_data.get('action', 'warn')
            }
            
            response = self.session.post(
                f"{self.router_url}/violations/report",
                json=report_data,
                timeout=Config.REQUEST_TIMEOUT
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error reporting violation: {str(e)}")
            return False