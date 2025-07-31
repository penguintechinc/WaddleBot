"""
Identity API Client for WaddleBot Portal
Calls the identity_core_module APIs
"""

import requests
import logging
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)

class IdentityAPIClient:
    """Client for interacting with WaddleBot Identity Core API"""
    
    def __init__(self):
        self.base_url = os.environ.get('IDENTITY_API_URL', 'http://identity-core:8050')
        self.api_key = os.environ.get('PORTAL_API_KEY', '')
        self.timeout = int(os.environ.get('API_TIMEOUT', '30'))
        
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None) -> Dict:
        """Make HTTP request to identity API"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code >= 400:
                logger.error(f"Identity API error {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"API error {response.status_code}",
                    "message": response.text
                }
            
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Identity API timeout for {endpoint}")
            return {"success": False, "error": "timeout"}
        except requests.exceptions.ConnectionError:
            logger.error(f"Identity API connection error for {endpoint}")
            return {"success": False, "error": "connection_error"}
        except Exception as e:
            logger.error(f"Identity API unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_identities(self, user_id: int) -> Dict:
        """Get all linked identities for a user"""
        return self._make_request('GET', f'/identity/user/{user_id}')
    
    def get_user_by_platform(self, platform: str, platform_id: str) -> Dict:
        """Get WaddleBot user by platform identity"""
        return self._make_request('GET', f'/identity/platform/{platform}/{platform_id}')
    
    def initiate_identity_link(self, user_id: int, source_platform: str, 
                              target_platform: str, target_username: str) -> Dict:
        """Initiate identity linking between platforms"""
        data = {
            'user_id': user_id,
            'source_platform': source_platform,
            'target_platform': target_platform,
            'target_username': target_username
        }
        return self._make_request('POST', '/identity/link', data)
    
    def verify_identity(self, platform: str, platform_id: str, 
                       platform_username: str, verification_code: str) -> Dict:
        """Verify identity with code"""
        data = {
            'platform': platform,
            'platform_id': platform_id,
            'platform_username': platform_username,
            'verification_code': verification_code
        }
        return self._make_request('POST', '/identity/verify', data)
    
    def unlink_identity(self, user_id: int, platform: str) -> Dict:
        """Unlink platform identity"""
        data = {
            'user_id': user_id,
            'platform': platform
        }
        return self._make_request('DELETE', '/identity/unlink', data)
    
    def get_pending_verifications(self, user_id: Optional[int] = None, 
                                 platform: Optional[str] = None) -> Dict:
        """Get pending verification requests"""
        params = {}
        if user_id:
            params['user_id'] = user_id
        if platform:
            params['platform'] = platform
        
        return self._make_request('GET', '/identity/pending', params=params)
    
    def resend_verification(self, user_id: int, target_platform: str) -> Dict:
        """Resend verification code"""
        data = {
            'user_id': user_id,
            'target_platform': target_platform
        }
        return self._make_request('POST', '/identity/resend', data)
    
    # ============ API Key Management ============
    
    def create_api_key(self, user_session_token: str, name: str, 
                      expires_in_days: int = 365) -> Dict:
        """Create API key for user"""
        headers = {
            **self.headers,
            'Authorization': f'Bearer {user_session_token}'
        }
        
        data = {
            'name': name,
            'expires_in_days': expires_in_days
        }
        
        try:
            url = f"{self.base_url}/identity/api-keys"
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            
            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"API error {response.status_code}",
                    "message": response.text
                }
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return {"success": False, "error": str(e)}
    
    def list_api_keys(self, user_session_token: str) -> Dict:
        """List user's API keys"""
        headers = {
            **self.headers,
            'Authorization': f'Bearer {user_session_token}'
        }
        
        try:
            url = f"{self.base_url}/identity/api-keys"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"API error {response.status_code}",
                    "message": response.text
                }
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return {"success": False, "error": str(e)}
    
    def revoke_api_key(self, user_session_token: str, key_id: int) -> Dict:
        """Revoke API key"""
        headers = {
            **self.headers,
            'Authorization': f'Bearer {user_session_token}'
        }
        
        try:
            url = f"{self.base_url}/identity/api-keys/{key_id}"
            response = requests.delete(url, headers=headers, timeout=self.timeout)
            
            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"API error {response.status_code}",
                    "message": response.text
                }
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error revoking API key: {e}")
            return {"success": False, "error": str(e)}
    
    def regenerate_api_key(self, user_session_token: str, key_id: int) -> Dict:
        """Regenerate API key"""
        headers = {
            **self.headers,
            'Authorization': f'Bearer {user_session_token}'
        }
        
        try:
            url = f"{self.base_url}/identity/api-keys/{key_id}/regenerate"
            response = requests.post(url, headers=headers, timeout=self.timeout)
            
            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"API error {response.status_code}",
                    "message": response.text
                }
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error regenerating API key: {e}")
            return {"success": False, "error": str(e)}
    
    # ============ OAuth Authentication ============
    
    def initiate_oauth_login(self, provider: str) -> str:
        """Get OAuth login URL"""
        return f"{self.base_url}/auth/oauth/{provider}"
    
    def register_user(self, username: str, email: str, password: str, 
                     first_name: str = '', last_name: str = '', 
                     display_name: str = '') -> Dict:
        """Register new user"""
        data = {
            'username': username,
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'display_name': display_name
        }
        return self._make_request('POST', '/auth/register', data)
    
    def login_user(self, username: str, password: str) -> Dict:
        """Login user"""
        data = {
            'username': username,
            'password': password
        }
        return self._make_request('POST', '/auth/login', data)
    
    def get_user_profile(self, user_session_token: str) -> Dict:
        """Get user profile"""
        headers = {
            **self.headers,
            'Authorization': f'Bearer {user_session_token}'
        }
        
        try:
            url = f"{self.base_url}/auth/profile"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"API error {response.status_code}",
                    "message": response.text
                }
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {"success": False, "error": str(e)}
    
    def get_identity_stats(self) -> Dict:
        """Get identity module statistics"""
        return self._make_request('GET', '/identity/stats')
    
    def health_check(self) -> Dict:
        """Check identity service health"""
        return self._make_request('GET', '/health')