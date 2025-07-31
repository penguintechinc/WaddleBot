"""
Platform Service for sending verification messages via whispers/DMs
"""

import requests
import logging
from datetime import datetime
import time
from ..config import Config
from ..logging_config import log_event

logger = logging.getLogger(Config.MODULE_NAME)

class PlatformService:
    """Service for interacting with platform collectors for whisper/DM functionality"""
    
    def __init__(self):
        self.platform_apis = {
            'twitch': Config.TWITCH_API_URL,
            'discord': Config.DISCORD_API_URL,
            'slack': Config.SLACK_API_URL
        }
        self.api_key = list(Config.VALID_API_KEYS)[0] if Config.VALID_API_KEYS else None
    
    def send_verification_message(self, platform, username, verification_code, 
                                 source_platform, source_username):
        """
        Send verification code to user via platform whisper/DM
        
        Args:
            platform: Target platform (twitch, discord, slack)
            username: Target username to send message to
            verification_code: Verification code to send
            source_platform: Platform where request originated
            source_username: Username on source platform
        """
        try:
            message = self._format_verification_message(
                verification_code, source_platform, source_username
            )
            
            # Get platform API URL
            api_url = self.platform_apis.get(platform)
            if not api_url:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Platform-specific whisper/DM endpoints
            if platform == 'twitch':
                success = self._send_twitch_whisper(api_url, username, message)
            elif platform == 'discord':
                success = self._send_discord_dm(api_url, username, message)
            elif platform == 'slack':
                success = self._send_slack_dm(api_url, username, message)
            else:
                raise ValueError(f"Platform {platform} not implemented")
            
            log_event(
                "AUDIT", "WHISPER",
                platform=platform,
                user=username,
                action="verification_sent",
                result="success" if success else "failed"
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send verification message: {e}")
            log_event(
                "ERROR", "WHISPER",
                platform=platform,
                user=username,
                action="verification_failed",
                result="error",
                details={"error": str(e)}
            )
            return False
    
    def _format_verification_message(self, code, source_platform, source_username):
        """Format the verification message"""
        return (
            f"🔐 WaddleBot Identity Verification\n\n"
            f"Someone from {source_platform} (@{source_username}) is trying to link "
            f"this account to their WaddleBot identity.\n\n"
            f"Verification Code: {code}\n\n"
            f"To confirm, type: !verify {code}\n\n"
            f"This code expires in {Config.VERIFICATION_TIMEOUT_MINUTES} minutes.\n"
            f"If this wasn't you, please ignore this message."
        )
    
    def _send_twitch_whisper(self, api_url, username, message):
        """Send whisper via Twitch collector"""
        try:
            # Call Twitch collector whisper endpoint
            response = requests.post(
                f"{api_url}/whisper",
                json={
                    "to_user": username,
                    "message": message
                },
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                },
                timeout=Config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Twitch whisper failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Twitch whisper error: {e}")
            return False
    
    def _send_discord_dm(self, api_url, username, message):
        """Send DM via Discord collector"""
        try:
            # Call Discord collector DM endpoint
            response = requests.post(
                f"{api_url}/dm",
                json={
                    "username": username,
                    "message": message
                },
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                },
                timeout=Config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Discord DM failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Discord DM error: {e}")
            return False
    
    def _send_slack_dm(self, api_url, username, message):
        """Send DM via Slack collector"""
        try:
            # Call Slack collector DM endpoint
            response = requests.post(
                f"{api_url}/dm",
                json={
                    "username": username,
                    "message": message
                },
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                },
                timeout=Config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Slack DM failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Slack DM error: {e}")
            return False
    
    def health_check(self):
        """Check health of platform APIs"""
        health_status = {}
        
        for platform, api_url in self.platform_apis.items():
            try:
                response = requests.get(
                    f"{api_url}/health",
                    timeout=5
                )
                health_status[platform] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                health_status[platform] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return health_status