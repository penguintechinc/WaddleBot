"""
Core API service for Discord collector module
Handles communication with WaddleBot core
"""

import os
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class CoreAPIClient:
    """Client for communicating with WaddleBot core API"""
    
    def __init__(self):
        self.base_url = os.environ.get("CORE_API_URL", "http://core-api:8001")
        self.context_url = os.environ.get("CONTEXT_API_URL", f"{self.base_url}/api/context")
        self.reputation_url = os.environ.get("REPUTATION_API_URL", f"{self.base_url}/api/reputation")
        self.gateway_url = os.environ.get("GATEWAY_ACTIVATE_URL", f"{self.base_url}/api/gateway/activate")
        
        # Module identification
        self.module_name = os.environ.get("MODULE_NAME", "discord")
        self.module_version = os.environ.get("MODULE_VERSION", "1.0.0")
        self.endpoint_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
        
        # Default headers
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": f"WaddleBot-{self.module_name}/{self.module_version}",
            "X-Module-Name": self.module_name,
            "X-Module-Version": self.module_version
        }
    
    def register_module(self) -> bool:
        """Register this collector module with the core"""
        try:
            registration_data = {
                "module_name": self.module_name,
                "module_version": self.module_version,
                "platform": "discord",
                "endpoint_url": self.endpoint_url,
                "health_check_url": f"{self.endpoint_url.replace('/webhook', '/health')}" if self.endpoint_url else "",
                "status": "active",
                "config": {
                    "supported_events": [
                        "on_message",
                        "on_reaction_add",
                        "on_member_join",
                        "on_member_remove",
                        "on_voice_state_update",
                        "on_guild_join",
                        "on_guild_remove",
                        "on_member_update"
                    ],
                    "bot_features": [
                        "slash_commands",
                        "message_processing",
                        "voice_tracking",
                        "reaction_tracking",
                        "member_tracking"
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/modules/register",
                json=registration_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully registered module {self.module_name}")
                return True
            else:
                logger.error(f"Failed to register module: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error registering module: {str(e)}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to core API"""
        try:
            heartbeat_data = {
                "module_name": self.module_name,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            response = requests.post(
                f"{self.base_url}/api/modules/heartbeat",
                json=heartbeat_data,
                headers=self.headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            logger.error(f"Error sending heartbeat: {str(e)}")
            return False
    
    def get_monitored_servers(self) -> List[Dict[str, Any]]:
        """Get list of servers this module should monitor"""
        try:
            response = requests.get(
                f"{self.base_url}/api/servers",
                params={"platform": "discord", "active": True},
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get("servers", [])
                logger.info(f"Retrieved {len(servers)} Discord servers to monitor")
                return servers
            else:
                logger.error(f"Failed to get servers: {response.status_code} - {response.text}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Error getting monitored servers: {str(e)}")
            return []
    
    def get_context(self, identity_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get user context from core API"""
        try:
            response = requests.post(
                self.context_url,
                json=identity_payload,
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data")
            else:
                logger.warning(f"Context API returned {response.status_code}: {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error getting context: {str(e)}")
            return None
    
    def send_reputation(self, context_payload: Dict[str, Any]) -> bool:
        """Send reputation data to core API"""
        try:
            response = requests.post(
                self.reputation_url,
                json=context_payload,
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                logger.info("Successfully sent reputation data")
                return True
            else:
                logger.warning(f"Reputation API returned {response.status_code}: {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error sending reputation: {str(e)}")
            return False
    
    def forward_event(self, event_data: Dict[str, Any]) -> bool:
        """Forward processed event to core API"""
        try:
            # Add metadata about the source module
            event_data["_metadata"] = {
                "source_module": self.module_name,
                "source_version": self.module_version,
                "processed_at": datetime.utcnow().isoformat(),
                "platform": "discord"
            }
            
            response = requests.post(
                f"{self.base_url}/api/events",
                json=event_data,
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                logger.info("Successfully forwarded event to core")
                return True
            else:
                logger.warning(f"Event forwarding failed: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error forwarding event: {str(e)}")
            return False
    
    def get_server_config(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific server"""
        try:
            response = requests.get(
                f"{self.base_url}/api/servers/{server_id}",
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Server config request failed: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error getting server config: {str(e)}")
            return None
    
    def update_server_activity(self, server_id: str, activity_data: Dict[str, Any]) -> bool:
        """Update last activity timestamp for a server"""
        try:
            response = requests.patch(
                f"{self.base_url}/api/servers/{server_id}/activity",
                json=activity_data,
                headers=self.headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            logger.error(f"Error updating server activity: {str(e)}")
            return False

# Global instance
core_api = CoreAPIClient()