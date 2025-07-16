import logging
import requests
import json
from typing import Dict, Any, Optional
import traceback

from config import Config

logger = logging.getLogger(__name__)

class RouterService:
    """Service for communicating with the WaddleBot router"""
    
    def __init__(self):
        self.router_url = Config.ROUTER_API_URL
        self.core_url = Config.CORE_API_URL
        self.session = requests.Session()
        self.session.timeout = Config.REQUEST_TIMEOUT
    
    def submit_response(self, response_data: Dict[str, Any]) -> bool:
        """Submit response back to the router"""
        try:
            url = f"{self.router_url}/responses"
            
            # Ensure required fields are present
            required_fields = ['session_id', 'module_name', 'success']
            for field in required_fields:
                if field not in response_data:
                    logger.error(f"Missing required field in response: {field}")
                    return False
            
            # Add default values for optional fields
            response_data.setdefault('response_action', 'chat')
            response_data.setdefault('processing_time_ms', 0)
            
            logger.info(f"Submitting response to router: {url}")
            logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
            
            response = self.session.post(
                url,
                json=response_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully submitted response for session {response_data['session_id']}")
                return True
            else:
                logger.error(f"Failed to submit response: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error submitting response to router: {str(e)}\n{traceback.format_exc()}")
            return False
    
    def register_module(self) -> bool:
        """Register this module with the core API"""
        try:
            url = f"{self.core_url}/api/modules/register"
            
            registration_data = {
                "module_name": Config.MODULE_NAME,
                "module_version": Config.MODULE_VERSION,
                "platform": "interaction",
                "endpoint_url": f"http://{Config.MODULE_NAME}:8000",
                "health_check_url": f"http://{Config.MODULE_NAME}:8000/health",
                "status": "active",
                "config": {
                    "supports_chat": True,
                    "supports_events": Config.RESPOND_TO_EVENTS,
                    "question_triggers": Config.QUESTION_TRIGGERS,
                    "event_types": Config.EVENT_RESPONSE_TYPES,
                    "model": Config.OLLAMA_MODEL,
                    "temperature": Config.OLLAMA_TEMPERATURE
                }
            }
            
            logger.info(f"Registering module with core API: {url}")
            response = self.session.post(
                url,
                json=registration_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully registered module {Config.MODULE_NAME}")
                return True
            else:
                logger.error(f"Failed to register module: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering module: {str(e)}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to core API"""
        try:
            url = f"{self.core_url}/api/modules/heartbeat"
            
            heartbeat_data = {
                "module_name": Config.MODULE_NAME,
                "status": "active",
                "last_activity": None,  # Could track this
                "config": {
                    "model": Config.OLLAMA_MODEL,
                    "temperature": Config.OLLAMA_TEMPERATURE,
                    "question_triggers": Config.QUESTION_TRIGGERS,
                    "respond_to_events": Config.RESPOND_TO_EVENTS
                }
            }
            
            response = self.session.post(
                url,
                json=heartbeat_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.debug(f"Sent heartbeat for module {Config.MODULE_NAME}")
                return True
            else:
                logger.warning(f"Failed to send heartbeat: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.warning(f"Error sending heartbeat: {str(e)}")
            return False
    
    def get_router_commands(self) -> Optional[list]:
        """Get available commands from router"""
        try:
            url = f"{self.router_url}/commands"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get router commands: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting router commands: {str(e)}")
            return None
    
    def register_interaction_commands(self) -> bool:
        """Register interaction commands with the router"""
        try:
            # Register commands that this module can handle
            commands = [
                {
                    "command": "ai",
                    "prefix": "!",
                    "description": "Ask the AI a question",
                    "location_url": f"http://{Config.MODULE_NAME}:8000/interaction",
                    "location": "internal",
                    "type": "container",
                    "method": "POST",
                    "timeout": Config.REQUEST_TIMEOUT,
                    "module_type": "interaction",
                    "module_id": Config.MODULE_NAME,
                    "trigger_type": "command",
                    "priority": 50
                },
                {
                    "command": "ask",
                    "prefix": "!",
                    "description": "Ask the AI assistant",
                    "location_url": f"http://{Config.MODULE_NAME}:8000/interaction",
                    "location": "internal",
                    "type": "container",
                    "method": "POST",
                    "timeout": Config.REQUEST_TIMEOUT,
                    "module_type": "interaction",
                    "module_id": Config.MODULE_NAME,
                    "trigger_type": "command",
                    "priority": 50
                }
            ]
            
            # If responding to events, register event handlers
            if Config.RESPOND_TO_EVENTS:
                for event_type in Config.EVENT_RESPONSE_TYPES:
                    commands.append({
                        "command": f"ai_response_{event_type}",
                        "prefix": "",
                        "description": f"AI response for {event_type} events",
                        "location_url": f"http://{Config.MODULE_NAME}:8000/interaction",
                        "location": "internal",
                        "type": "container",
                        "method": "POST",
                        "timeout": Config.REQUEST_TIMEOUT,
                        "module_type": "interaction",
                        "module_id": Config.MODULE_NAME,
                        "trigger_type": "event",
                        "event_types": [event_type],
                        "priority": 100
                    })
            
            # Register each command
            success_count = 0
            for command in commands:
                if self._register_single_command(command):
                    success_count += 1
            
            logger.info(f"Registered {success_count}/{len(commands)} commands")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error registering commands: {str(e)}")
            return False
    
    def _register_single_command(self, command_data: Dict[str, Any]) -> bool:
        """Register a single command with the router"""
        try:
            url = f"{self.router_url}/commands"
            
            response = self.session.post(
                url,
                json=command_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Registered command: {command_data.get('command', 'unknown')}")
                return True
            else:
                logger.error(f"Failed to register command {command_data.get('command')}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering command {command_data.get('command')}: {str(e)}")
            return False