"""
Unit tests for Identity API Client
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
import json
import sys
import os

# Add the portal module path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestIdentityAPIClient(unittest.TestCase):
    """Test cases for IdentityAPIClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Import after setting up path
        from services.identity_api_client import IdentityAPIClient
        
        # Create client with test configuration
        with patch.dict(os.environ, {
            'IDENTITY_API_URL': 'http://test-identity:8050',
            'PORTAL_API_KEY': 'test_api_key',
            'API_TIMEOUT': '30'
        }):
            self.client = IdentityAPIClient()
    
    @patch('services.identity_api_client.requests.request')
    def test_make_request_success(self, mock_request):
        """Test successful API request"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'data': 'test'}
        mock_request.return_value = mock_response
        
        # Test
        result = self.client._make_request('GET', '/test')
        
        # Verify
        self.assertEqual(result, {'success': True, 'data': 'test'})
        mock_request.assert_called_once_with(
            method='GET',
            url='http://test-identity:8050/test',
            json=None,
            params=None,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.request')
    def test_make_request_http_error(self, mock_request):
        """Test API request with HTTP error"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_request.return_value = mock_response
        
        # Test
        result = self.client._make_request('GET', '/test')
        
        # Verify
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'API error 400')
        self.assertEqual(result['message'], 'Bad Request')
    
    @patch('services.identity_api_client.requests.request')
    def test_make_request_timeout(self, mock_request):
        """Test API request timeout"""
        # Setup mock to raise timeout
        mock_request.side_effect = requests.exceptions.Timeout()
        
        # Test
        result = self.client._make_request('GET', '/test')
        
        # Verify
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'timeout')
    
    @patch('services.identity_api_client.requests.request')
    def test_make_request_connection_error(self, mock_request):
        """Test API request connection error"""
        # Setup mock to raise connection error
        mock_request.side_effect = requests.exceptions.ConnectionError()
        
        # Test
        result = self.client._make_request('GET', '/test')
        
        # Verify
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'connection_error')
    
    @patch('services.identity_api_client.requests.request')
    def test_get_user_identities(self, mock_request):
        """Test getting user identities"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user_id': '123',
            'identities': [
                {'platform': 'discord', 'platform_username': 'user123'},
                {'platform': 'twitch', 'platform_username': 'streamer123'}
            ]
        }
        mock_request.return_value = mock_response
        
        # Test
        result = self.client.get_user_identities(123)
        
        # Verify
        self.assertEqual(result['user_id'], '123')
        self.assertEqual(len(result['identities']), 2)
        mock_request.assert_called_once_with(
            method='GET',
            url='http://test-identity:8050/identity/user/123',
            json=None,
            params=None,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.request')
    def test_get_user_by_platform(self, mock_request):
        """Test getting user by platform"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user_id': '123',
            'platform': 'discord',
            'platform_id': '456789',
            'platform_username': 'user123'
        }
        mock_request.return_value = mock_response
        
        # Test
        result = self.client.get_user_by_platform('discord', '456789')
        
        # Verify
        self.assertEqual(result['user_id'], '123')
        self.assertEqual(result['platform'], 'discord')
        mock_request.assert_called_once_with(
            method='GET',
            url='http://test-identity:8050/identity/platform/discord/456789',
            json=None,
            params=None,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.request')
    def test_initiate_identity_link(self, mock_request):
        """Test initiating identity link"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'message': 'Verification code sent'
        }
        mock_request.return_value = mock_response
        
        # Test
        result = self.client.initiate_identity_link(123, 'discord', 'twitch', 'streamer123')
        
        # Verify
        self.assertTrue(result['success'])
        mock_request.assert_called_once_with(
            method='POST',
            url='http://test-identity:8050/identity/link',
            json={
                'user_id': 123,
                'source_platform': 'discord',
                'target_platform': 'twitch',
                'target_username': 'streamer123'
            },
            params=None,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.request')
    def test_verify_identity(self, mock_request):
        """Test identity verification"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'message': 'Identity verified successfully',
            'user_id': '123'
        }
        mock_request.return_value = mock_response
        
        # Test
        result = self.client.verify_identity('twitch', '789456', 'streamer123', 'ABC123')
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['user_id'], '123')
        mock_request.assert_called_once_with(
            method='POST',
            url='http://test-identity:8050/identity/verify',
            json={
                'platform': 'twitch',
                'platform_id': '789456',
                'platform_username': 'streamer123',
                'verification_code': 'ABC123'
            },
            params=None,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.post')
    def test_create_api_key(self, mock_post):
        """Test creating API key"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'key_id': 456,
            'api_key': 'wbot_user_test_key',
            'name': 'Test Key'
        }
        mock_post.return_value = mock_response
        
        # Test
        result = self.client.create_api_key('user_session_token', 'Test Key', 365)
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['key_id'], 456)
        mock_post.assert_called_once_with(
            'http://test-identity:8050/identity/api-keys',
            json={
                'name': 'Test Key',
                'expires_in_days': 365
            },
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key',
                'Authorization': 'Bearer user_session_token'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.get')
    def test_list_api_keys(self, mock_get):
        """Test listing API keys"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'api_keys': [
                {'key_id': 1, 'name': 'Key 1'},
                {'key_id': 2, 'name': 'Key 2'}
            ]
        }
        mock_get.return_value = mock_response
        
        # Test
        result = self.client.list_api_keys('user_session_token')
        
        # Verify
        self.assertIn('api_keys', result)
        self.assertEqual(len(result['api_keys']), 2)
        mock_get.assert_called_once_with(
            'http://test-identity:8050/identity/api-keys',
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key',
                'Authorization': 'Bearer user_session_token'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.delete')
    def test_revoke_api_key(self, mock_delete):
        """Test revoking API key"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'message': 'API key revoked successfully'
        }
        mock_delete.return_value = mock_response
        
        # Test
        result = self.client.revoke_api_key('user_session_token', 456)
        
        # Verify
        self.assertTrue(result['success'])
        mock_delete.assert_called_once_with(
            'http://test-identity:8050/identity/api-keys/456',
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key',
                'Authorization': 'Bearer user_session_token'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.post')
    def test_regenerate_api_key(self, mock_post):
        """Test regenerating API key"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'api_key': 'wbot_user_new_key',
            'message': 'API key regenerated successfully'
        }
        mock_post.return_value = mock_response
        
        # Test
        result = self.client.regenerate_api_key('user_session_token', 456)
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['api_key'], 'wbot_user_new_key')
        mock_post.assert_called_once_with(
            'http://test-identity:8050/identity/api-keys/456/regenerate',
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key',
                'Authorization': 'Bearer user_session_token'
            },
            timeout=30
        )
    
    def test_initiate_oauth_login(self):
        """Test getting OAuth login URL"""
        result = self.client.initiate_oauth_login('discord')
        expected = 'http://test-identity:8050/auth/oauth/discord'
        self.assertEqual(result, expected)
    
    @patch('services.identity_api_client.requests.request')
    def test_register_user(self, mock_request):
        """Test user registration"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'message': 'User registered successfully',
            'user_id': '123'
        }
        mock_request.return_value = mock_response
        
        # Test
        result = self.client.register_user(
            'testuser', 'test@example.com', 'password123',
            'Test', 'User', 'Test User'
        )
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['user_id'], '123')
        mock_request.assert_called_once_with(
            method='POST',
            url='http://test-identity:8050/auth/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'first_name': 'Test',
                'last_name': 'User',
                'display_name': 'Test User'
            },
            params=None,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key'
            },
            timeout=30
        )
    
    @patch('services.identity_api_client.requests.request')
    def test_health_check(self, mock_request):
        """Test health check"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'healthy',
            'module': 'identity_core_module',
            'version': '1.0.0'
        }
        mock_request.return_value = mock_response
        
        # Test
        result = self.client.health_check()
        
        # Verify
        self.assertEqual(result['status'], 'healthy')
        mock_request.assert_called_once_with(
            method='GET',
            url='http://test-identity:8050/health',
            json=None,
            params=None,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key'
            },
            timeout=30
        )

if __name__ == '__main__':
    unittest.main()