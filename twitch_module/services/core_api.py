"""
Core API service for communicating with WaddleBot core
Handles server list retrieval and event forwarding
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
        self.module_name = os.environ.get("MODULE_NAME", "twitch")
        self.module_version = os.environ.get("MODULE_VERSION", "1.0.0")
        self.endpoint_url = os.environ.get("TWITCH_WEBHOOK_CALLBACK_URL", "")
        
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
                "platform": "twitch",
                "endpoint_url": self.endpoint_url,
                "health_check_url": f"{self.endpoint_url.replace('/webhook', '/health')}",
                "status": "active",
                "config": {
                    "supported_events": [
                        "channel.follow",
                        "channel.subscribe",
                        "channel.cheer", 
                        "channel.raid",
                        "channel.subscription.gift"
                    ],
                    "webhook_url": self.endpoint_url
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
                params={"platform": "twitch", "active": True},
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get("servers", [])
                logger.info(f"Retrieved {len(servers)} Twitch servers to monitor")
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
    
    def activate_gateway(self, activation_key: str) -> Dict[str, Any]:
        """Activate gateway through core API"""
        try:
            response = requests.post(
                self.gateway_url,
                json={"activation_key": activation_key},
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Gateway activation failed: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}"}
                
        except requests.RequestException as e:
            logger.error(f"Error activating gateway: {str(e)}")
            return {"error": str(e)}
    
    def forward_event(self, event_data: Dict[str, Any]) -> bool:
        """Forward processed event to core API"""
        try:
            # Add metadata about the source module
            event_data["_metadata"] = {
                "source_module": self.module_name,
                "source_version": self.module_version,
                "processed_at": datetime.utcnow().isoformat(),
                "platform": "twitch"
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
    
    def send_command_to_router(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to router for command processing"""
        try:
            # Ensure message_type is included
            if "message_type" not in message_data:
                message_data["message_type"] = "chatMessage"  # Default for user messages
            
            response = requests.post(
                f"{self.base_url}/router/events",
                json=message_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Router processed message: {result.get('processed', False)}")
                return result
            else:
                logger.warning(f"Router request failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except requests.RequestException as e:
            logger.error(f"Error sending message to router: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_module_responses(self, execution_id: str) -> Dict[str, Any]:
        """Get module responses for an execution"""
        try:
            response = requests.get(
                f"{self.base_url}/router/responses/{execution_id}",
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Response request failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except requests.RequestException as e:
            logger.error(f"Error getting module responses: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_form_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process form response for Twitch platform"""
        try:
            if response_data.get("response_action") != "form":
                return {"success": False, "error": "Not a form response"}
            
            # Extract form data
            form_data = {
                "title": response_data.get("form_title", "Form"),
                "description": response_data.get("form_description", ""),
                "fields": response_data.get("form_fields", []),
                "submit_url": response_data.get("form_submit_url", ""),
                "submit_method": response_data.get("form_submit_method", "POST"),
                "callback_url": response_data.get("form_callback_url", "")
            }
            
            # For Twitch, we need to convert form to chat message format
            # Since Twitch doesn't have native forms, we'll create a chat response
            # with instructions on how to use the form
            
            form_message = f"📋 {form_data['title']}"
            if form_data['description']:
                form_message += f"\n{form_data['description']}"
            
            form_message += "\n\nFields:"
            for field in form_data['fields']:
                field_name = field.get('name', 'field')
                field_type = field.get('type', 'text')
                field_label = field.get('label', field_name)
                field_required = field.get('required', False)
                
                form_message += f"\n• {field_label} ({field_type})"
                if field_required:
                    form_message += " *required*"
                
                # Add field options for select/radio fields
                if field_type in ['select', 'radio', 'multiselect'] and field.get('options'):
                    options = field.get('options', [])
                    form_message += f" - Options: {', '.join(options)}"
            
            if form_data['submit_url']:
                form_message += f"\n\nSubmit to: {form_data['submit_url']}"
            
            return {
                "success": True,
                "platform_response": {
                    "type": "chat",
                    "message": form_message,
                    "form_data": form_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing form response: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_twitch_event_to_router(self, event_type: str, user_id: str, user_name: str, 
                                   channel_id: str, event_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send Twitch-specific events to router"""
        try:
            # Map Twitch event types to message types
            event_type_mapping = {
                "channel.follow": "follow",
                "channel.subscribe": "subscription",
                "channel.subscription.gift": "subgift",
                "channel.subscription.message": "resub",
                "channel.cheer": "cheer",
                "channel.raid": "raid",
                "channel.host": "host",
                "channel.ban": "ban",
                "channel.moderator.add": "member_join",
                "channel.moderator.remove": "member_leave",
                "user.message": "chatMessage"
            }
            
            message_type = event_type_mapping.get(event_type, "chatMessage")
            
            # Prepare message data
            message_data = {
                "platform": "twitch",
                "server_id": channel_id,
                "channel_id": "",  # Twitch doesn't have sub-channels
                "user_id": user_id,
                "user_name": user_name,
                "message_content": event_data.get("message", "") if event_data else "",
                "message_type": message_type
            }
            
            # Add event-specific data
            if event_data:
                message_data.update(event_data)
            
            return self.send_command_to_router(message_data)
            
        except Exception as e:
            logger.error(f"Error sending Twitch event to router: {str(e)}")
            return {"success": False, "error": str(e)}
    
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