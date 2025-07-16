import requests
import logging
import json
import secrets
import string
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import traceback

from config import Config

logger = logging.getLogger(__name__)


class KongAdminClient:
    """Kong Admin API client for managing consumers, API keys, and ACLs"""
    
    def __init__(self):
        self.admin_url = Config.KONG_ADMIN_URL.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = Config.REQUEST_TIMEOUT
        
        # Set basic auth if configured
        if Config.KONG_ADMIN_USERNAME and Config.KONG_ADMIN_PASSWORD:
            self.session.auth = (Config.KONG_ADMIN_USERNAME, Config.KONG_ADMIN_PASSWORD)
    
    def health_check(self) -> bool:
        """Check if Kong Admin API is accessible"""
        try:
            response = self.session.get(f"{self.admin_url}/status")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Kong health check failed: {str(e)}")
            return False
    
    def create_consumer(self, username: str, custom_id: Optional[str] = None, 
                       tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new Kong consumer"""
        try:
            payload = {"username": username}
            
            if custom_id:
                payload["custom_id"] = custom_id
            
            if tags:
                payload["tags"] = tags
            
            response = self.session.post(
                f"{self.admin_url}/consumers", 
                json=payload
            )
            
            if response.status_code == 201:
                consumer_data = response.json()
                logger.info(f"Created Kong consumer: {username} (ID: {consumer_data['id']})")
                return consumer_data
            elif response.status_code == 409:
                # Consumer already exists, get existing consumer
                logger.warning(f"Consumer {username} already exists, retrieving existing")
                return self.get_consumer(username)
            else:
                error_msg = f"Failed to create consumer {username}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error creating Kong consumer {username}: {str(e)}")
            raise
    
    def get_consumer(self, username: str) -> Optional[Dict[str, Any]]:
        """Get Kong consumer by username"""
        try:
            response = self.session.get(f"{self.admin_url}/consumers/{username}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                error_msg = f"Failed to get consumer {username}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error getting Kong consumer {username}: {str(e)}")
            raise
    
    def delete_consumer(self, username: str) -> bool:
        """Delete Kong consumer by username"""
        try:
            response = self.session.delete(f"{self.admin_url}/consumers/{username}")
            
            if response.status_code == 204:
                logger.info(f"Deleted Kong consumer: {username}")
                return True
            elif response.status_code == 404:
                logger.warning(f"Consumer {username} not found for deletion")
                return True  # Already deleted
            else:
                error_msg = f"Failed to delete consumer {username}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"Error deleting Kong consumer {username}: {str(e)}")
            return False
    
    def generate_api_key(self, length: int = None) -> str:
        """Generate a secure API key"""
        if length is None:
            length = Config.API_KEY_LENGTH
        
        # Generate secure random string
        alphabet = string.ascii_letters + string.digits
        api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
        return f"wbot_{api_key}"
    
    def create_api_key(self, consumer_username: str, api_key: Optional[str] = None,
                      tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create API key for Kong consumer"""
        try:
            if not api_key:
                api_key = self.generate_api_key()
            
            payload = {"key": api_key}
            
            if tags:
                payload["tags"] = tags
            
            response = self.session.post(
                f"{self.admin_url}/consumers/{consumer_username}/key-auth",
                json=payload
            )
            
            if response.status_code == 201:
                key_data = response.json()
                logger.info(f"Created API key for consumer: {consumer_username}")
                return key_data
            else:
                error_msg = f"Failed to create API key for {consumer_username}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error creating API key for {consumer_username}: {str(e)}")
            raise
    
    def get_consumer_api_keys(self, consumer_username: str) -> List[Dict[str, Any]]:
        """Get all API keys for a Kong consumer"""
        try:
            response = self.session.get(f"{self.admin_url}/consumers/{consumer_username}/key-auth")
            
            if response.status_code == 200:
                return response.json().get('data', [])
            else:
                error_msg = f"Failed to get API keys for {consumer_username}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error getting API keys for {consumer_username}: {str(e)}")
            raise
    
    def delete_api_key(self, consumer_username: str, key_id: str) -> bool:
        """Delete API key for Kong consumer"""
        try:
            response = self.session.delete(f"{self.admin_url}/consumers/{consumer_username}/key-auth/{key_id}")
            
            if response.status_code == 204:
                logger.info(f"Deleted API key {key_id} for consumer: {consumer_username}")
                return True
            elif response.status_code == 404:
                logger.warning(f"API key {key_id} not found for consumer {consumer_username}")
                return True  # Already deleted
            else:
                error_msg = f"Failed to delete API key {key_id}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"Error deleting API key {key_id}: {str(e)}")
            return False
    
    def add_consumer_to_acl_group(self, consumer_username: str, group: str) -> Dict[str, Any]:
        """Add Kong consumer to ACL group"""
        try:
            payload = {"group": group}
            
            response = self.session.post(
                f"{self.admin_url}/consumers/{consumer_username}/acls",
                json=payload
            )
            
            if response.status_code == 201:
                acl_data = response.json()
                logger.info(f"Added consumer {consumer_username} to ACL group: {group}")
                return acl_data
            elif response.status_code == 409:
                logger.warning(f"Consumer {consumer_username} already in ACL group: {group}")
                return {"group": group, "consumer": {"username": consumer_username}}
            else:
                error_msg = f"Failed to add {consumer_username} to ACL group {group}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error adding {consumer_username} to ACL group {group}: {str(e)}")
            raise
    
    def get_consumer_acl_groups(self, consumer_username: str) -> List[Dict[str, Any]]:
        """Get ACL groups for Kong consumer"""
        try:
            response = self.session.get(f"{self.admin_url}/consumers/{consumer_username}/acls")
            
            if response.status_code == 200:
                return response.json().get('data', [])
            else:
                error_msg = f"Failed to get ACL groups for {consumer_username}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error getting ACL groups for {consumer_username}: {str(e)}")
            raise
    
    def remove_consumer_from_acl_group(self, consumer_username: str, acl_id: str) -> bool:
        """Remove Kong consumer from ACL group"""
        try:
            response = self.session.delete(f"{self.admin_url}/consumers/{consumer_username}/acls/{acl_id}")
            
            if response.status_code == 204:
                logger.info(f"Removed consumer {consumer_username} from ACL group (ID: {acl_id})")
                return True
            elif response.status_code == 404:
                logger.warning(f"ACL {acl_id} not found for consumer {consumer_username}")
                return True  # Already removed
            else:
                error_msg = f"Failed to remove ACL {acl_id}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"Error removing ACL {acl_id}: {str(e)}")
            return False
    
    def list_all_consumers(self, size: int = 100, offset: str = None) -> Dict[str, Any]:
        """List all Kong consumers with pagination"""
        try:
            params = {"size": size}
            if offset:
                params["offset"] = offset
            
            response = self.session.get(f"{self.admin_url}/consumers", params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Failed to list consumers: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error listing consumers: {str(e)}")
            raise
    
    def backup_consumer(self, consumer_username: str) -> Dict[str, Any]:
        """Create a complete backup of Kong consumer configuration"""
        try:
            # Get consumer data
            consumer = self.get_consumer(consumer_username)
            if not consumer:
                raise Exception(f"Consumer {consumer_username} not found")
            
            # Get API keys
            api_keys = self.get_consumer_api_keys(consumer_username)
            
            # Get ACL groups
            acl_groups = self.get_consumer_acl_groups(consumer_username)
            
            backup_data = {
                "consumer": consumer,
                "api_keys": api_keys,
                "acl_groups": acl_groups,
                "backup_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Created backup for consumer: {consumer_username}")
            return backup_data
            
        except Exception as e:
            logger.error(f"Error backing up consumer {consumer_username}: {str(e)}")
            raise
    
    def get_kong_info(self) -> Dict[str, Any]:
        """Get Kong server information"""
        try:
            response = self.session.get(f"{self.admin_url}/")
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Failed to get Kong info: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error getting Kong info: {str(e)}")
            raise