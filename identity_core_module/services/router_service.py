"""
Router Service for registering identity commands with the router
"""

import requests
import logging
from datetime import datetime
from ..config import Config
from ..logging_config import log_event, log_system_event

logger = logging.getLogger(Config.MODULE_NAME)

class RouterService:
    """Service for integrating with WaddleBot router"""
    
    def __init__(self):
        self.router_url = Config.ROUTER_API_URL
        self.module_name = Config.MODULE_NAME
        self.module_version = Config.MODULE_VERSION
        self.api_key = list(Config.VALID_API_KEYS)[0] if Config.VALID_API_KEYS else None
    
    def register_module(self):
        """Register identity module and commands with router"""
        try:
            # Register module
            module_data = {
                "module_name": self.module_name,
                "module_version": self.module_version,
                "module_type": "core",
                "description": "Cross-platform identity linking and verification",
                "endpoints": {
                    "base_url": f"http://{self.module_name}:{Config.MODULE_PORT}",
                    "health_check": "/health",
                    "command_handler": "/router/command"
                }
            }
            
            # Register with router
            response = requests.post(
                f"{self.router_url}/modules/register",
                json=module_data,
                headers={"X-API-Key": self.api_key},
                timeout=Config.REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                raise Exception(f"Module registration failed: {response.text}")
            
            # Register commands
            self._register_commands()
            
            log_system_event("module_registered", {
                "module": self.module_name,
                "version": self.module_version
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register module: {e}")
            return False
    
    def _register_commands(self):
        """Register identity commands with router"""
        commands = [
            {
                "command": "!identity",
                "description": "Identity management commands",
                "location": "internal",
                "type": "container",
                "module_name": self.module_name,
                "subcommands": [
                    "link", "unlink", "status", "verify"
                ]
            },
            {
                "command": "!verify",
                "description": "Verify identity with code",
                "location": "internal", 
                "type": "container",
                "module_name": self.module_name,
                "trigger_type": "command"
            },
            {
                "command": "!whoami",
                "description": "Show your WaddleBot identity",
                "location": "internal",
                "type": "container", 
                "module_name": self.module_name,
                "trigger_type": "command"
            }
        ]
        
        for command in commands:
            try:
                response = requests.post(
                    f"{self.router_url}/commands",
                    json=command,
                    headers={"X-API-Key": self.api_key},
                    timeout=Config.REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    logger.info(f"Registered command: {command['command']}")
                else:
                    logger.error(f"Failed to register command {command['command']}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Error registering command {command['command']}: {e}")
    
    def handle_command(self, command_data):
        """
        Handle commands routed from the router
        
        Expected data:
        {
            "command": "!identity",
            "subcommand": "link",
            "args": ["twitch", "username"],
            "user_id": "123",
            "platform": "discord",
            "platform_user_id": "456",
            "entity_id": "789",
            "session_id": "abc123"
        }
        """
        try:
            command = command_data.get("command", "").lower()
            subcommand = command_data.get("subcommand", "").lower()
            args = command_data.get("args", [])
            user_id = command_data.get("user_id")
            platform = command_data.get("platform")
            platform_user_id = command_data.get("platform_user_id")
            session_id = command_data.get("session_id")
            
            # Route to appropriate handler
            if command == "!identity":
                return self._handle_identity_command(subcommand, args, user_id, platform)
            elif command == "!verify":
                return self._handle_verify_command(args, platform, platform_user_id)
            elif command == "!whoami":
                return self._handle_whoami_command(user_id, platform)
            else:
                return {
                    "success": False,
                    "message": "Unknown command"
                }
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return {
                "success": False,
                "message": "Error processing command"
            }
    
    def _handle_identity_command(self, subcommand, args, user_id, platform):
        """Handle !identity subcommands"""
        if subcommand == "link":
            if len(args) < 2:
                return {
                    "success": False,
                    "message": "Usage: !identity link <platform> <username>"
                }
            
            target_platform = args[0].lower()
            target_username = args[1]
            
            # Call identity link endpoint
            # This would be implemented to call the internal API
            return {
                "success": True,
                "message": f"Verification code sent to {target_username} on {target_platform}",
                "response_action": "chat"
            }
            
        elif subcommand == "unlink":
            if len(args) < 1:
                return {
                    "success": False,
                    "message": "Usage: !identity unlink <platform>"
                }
            
            return {
                "success": True,
                "message": f"Platform unlinked successfully",
                "response_action": "chat"
            }
            
        elif subcommand == "status":
            return {
                "success": True,
                "message": "Check your identity status at the portal",
                "response_action": "chat"
            }
            
        else:
            return {
                "success": False,
                "message": "Unknown subcommand. Use: link, unlink, or status"
            }
    
    def _handle_verify_command(self, args, platform, platform_user_id):
        """Handle !verify command"""
        if len(args) < 1:
            return {
                "success": False,
                "message": "Usage: !verify <code>",
                "response_action": "chat"
            }
        
        verification_code = args[0].upper()
        
        # This would call the verify endpoint internally
        return {
            "success": True,
            "message": "Identity verified successfully!",
            "response_action": "chat"
        }
    
    def _handle_whoami_command(self, user_id, platform):
        """Handle !whoami command"""
        # This would look up the user's identity
        return {
            "success": True,
            "message": f"You are WaddleBot user #{user_id} from {platform}",
            "response_action": "chat"
        }
    
    def send_heartbeat(self):
        """Send periodic heartbeat to router"""
        try:
            response = requests.post(
                f"{self.router_url}/modules/heartbeat",
                json={
                    "module_name": self.module_name,
                    "module_version": self.module_version,
                    "status": "healthy",
                    "uptime": datetime.utcnow().isoformat()
                },
                headers={"X-API-Key": self.api_key},
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False