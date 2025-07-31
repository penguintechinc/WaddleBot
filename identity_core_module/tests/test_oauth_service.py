"""
Unit tests for OAuth Service
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add the module path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestOAuthService(unittest.TestCase):
    """Test cases for OAuthService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock database and services
        self.mock_db = Mock()
        self.mock_redis = Mock()
        self.mock_identity_service = Mock()
        
        # Mock database tables
        self.mock_db.oauth_user_cache = Mock()
        self.mock_db.platform_identities = Mock()
        
        # Import after mocking
        from services.oauth_service import OAuthService
        self.oauth_service = OAuthService(
            self.mock_db, 
            self.mock_redis, 
            self.mock_identity_service
        )
    
    def test_extract_platform_id_discord(self):
        """Test extracting Discord platform ID"""
        user_data = {'id': '123456789'}
        result = self.oauth_service._extract_platform_id('discord', user_data)
        self.assertEqual(result, '123456789')
    
    def test_extract_platform_id_twitch(self):
        """Test extracting Twitch platform ID"""
        user_data = {'id': '98765432'}
        result = self.oauth_service._extract_platform_id('twitch', user_data)
        self.assertEqual(result, '98765432')
    
    def test_extract_platform_id_slack(self):
        """Test extracting Slack platform ID"""
        user_data = {'user': {'id': 'U123ABC'}}
        result = self.oauth_service._extract_platform_id('slack', user_data)
        self.assertEqual(result, 'U123ABC')
    
    def test_extract_username_discord(self):
        """Test extracting Discord username"""
        user_data = {'username': 'testuser123'}
        result = self.oauth_service._extract_username('discord', user_data)
        self.assertEqual(result, 'testuser123')
    
    def test_extract_username_twitch(self):
        """Test extracting Twitch username"""
        user_data = {'login': 'streamer_name'}
        result = self.oauth_service._extract_username('twitch', user_data)
        self.assertEqual(result, 'streamer_name')
    
    def test_extract_username_slack(self):
        """Test extracting Slack username"""
        user_data = {'user': {'name': 'slack.user'}}
        result = self.oauth_service._extract_username('slack', user_data)
        self.assertEqual(result, 'slack.user')
    
    def test_extract_email_discord(self):
        """Test extracting Discord email"""
        user_data = {'email': 'user@discord.com'}
        result = self.oauth_service._extract_email('discord', user_data)
        self.assertEqual(result, 'user@discord.com')
    
    def test_extract_display_name_discord(self):
        """Test extracting Discord display name"""
        user_data = {'global_name': 'Test User', 'username': 'testuser'}
        result = self.oauth_service._extract_display_name('discord', user_data)
        self.assertEqual(result, 'Test User')
        
        # Test fallback to username
        user_data = {'username': 'testuser'}
        result = self.oauth_service._extract_display_name('discord', user_data)
        self.assertEqual(result, 'testuser')
    
    def test_extract_avatar_url_discord(self):
        """Test extracting Discord avatar URL"""
        user_data = {'id': '123456', 'avatar': 'abc123def456'}
        result = self.oauth_service._extract_avatar_url('discord', user_data)
        expected = "https://cdn.discordapp.com/avatars/123456/abc123def456.png"
        self.assertEqual(result, expected)
    
    def test_extract_avatar_url_twitch(self):
        """Test extracting Twitch avatar URL"""
        user_data = {'profile_image_url': 'https://twitch.tv/avatar.jpg'}
        result = self.oauth_service._extract_avatar_url('twitch', user_data)
        self.assertEqual(result, 'https://twitch.tv/avatar.jpg')
    
    def test_handle_oauth_callback_success(self):
        """Test successful OAuth callback handling"""
        user_data = {
            'id': '123456',
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        mock_auth_user = Mock()
        mock_auth_user.id = 100
        mock_auth_user.primary_platform = None
        mock_auth_user.update_record = Mock()
        
        # Mock identity service success
        self.mock_identity_service.create_identity_link.return_value = True
        
        # Test
        result = self.oauth_service.handle_oauth_callback('discord', user_data, mock_auth_user)
        
        # Verify
        self.assertTrue(result)
        mock_auth_user.update_record.assert_called_with(primary_platform='discord')
        self.mock_identity_service.create_identity_link.assert_called_once()
    
    def test_handle_oauth_callback_missing_data(self):
        """Test OAuth callback with missing platform data"""
        user_data = {}  # Missing required data
        
        mock_auth_user = Mock()
        mock_auth_user.id = 100
        
        # Test
        result = self.oauth_service.handle_oauth_callback('discord', user_data, mock_auth_user)
        
        # Verify failure
        self.assertFalse(result)
    
    def test_handle_oauth_callback_identity_link_failure(self):
        """Test OAuth callback when identity linking fails"""
        user_data = {
            'id': '123456',
            'username': 'testuser'
        }
        
        mock_auth_user = Mock()
        mock_auth_user.id = 100
        mock_auth_user.primary_platform = 'twitch'
        
        # Mock identity service failure
        self.mock_identity_service.create_identity_link.return_value = False
        
        # Test
        result = self.oauth_service.handle_oauth_callback('discord', user_data, mock_auth_user)
        
        # Verify failure
        self.assertFalse(result)
    
    def test_cache_oauth_user_data_new_record(self):
        """Test caching OAuth user data for new user"""
        # Setup mock query to return no existing record
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = None
        self.mock_db.__call__.return_value = mock_query
        
        # Setup insert mock
        self.mock_db.oauth_user_cache.insert = Mock()
        self.mock_db.commit = Mock()
        
        user_data = {
            'id': '123456',
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        # Test
        self.oauth_service._cache_oauth_user_data(100, 'discord', user_data, '123456', 'testuser')
        
        # Verify insert was called
        self.mock_db.oauth_user_cache.insert.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    def test_cache_oauth_user_data_existing_record(self):
        """Test caching OAuth user data for existing user"""
        # Setup mock query to return existing record
        mock_existing_record = Mock()
        mock_existing_record.update_record = Mock()
        
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_existing_record
        self.mock_db.__call__.return_value = mock_query
        
        self.mock_db.commit = Mock()
        
        user_data = {
            'id': '123456',
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        # Test
        self.oauth_service._cache_oauth_user_data(100, 'discord', user_data, '123456', 'testuser')
        
        # Verify update was called
        mock_existing_record.update_record.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    def test_get_oauth_user_cache_found(self):
        """Test getting OAuth user cache when record exists"""
        mock_cache_record = Mock()
        mock_cache_record.provider_user_id = '123456'
        mock_cache_record.provider_username = 'testuser'
        mock_cache_record.provider_email = 'test@example.com'
        mock_cache_record.provider_display_name = 'Test User'
        mock_cache_record.provider_avatar_url = 'https://example.com/avatar.jpg'
        mock_cache_record.raw_user_data = {'id': '123456'}
        mock_cache_record.last_updated = datetime.utcnow()
        
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_cache_record
        self.mock_db.__call__.return_value = mock_query
        
        # Test
        result = self.oauth_service.get_oauth_user_cache(100, 'discord')
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result['provider_user_id'], '123456')
        self.assertEqual(result['provider_username'], 'testuser')
    
    def test_get_oauth_user_cache_not_found(self):
        """Test getting OAuth user cache when record doesn't exist"""
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = None
        self.mock_db.__call__.return_value = mock_query
        
        # Test
        result = self.oauth_service.get_oauth_user_cache(100, 'discord')
        
        # Verify
        self.assertIsNone(result)
    
    def test_revoke_oauth_connection_success(self):
        """Test successful OAuth connection revocation"""
        # Setup delete mocks
        mock_cache_delete = Mock()
        mock_tokens_delete = Mock()
        
        self.mock_db.__call__.side_effect = [mock_cache_delete, mock_tokens_delete]
        mock_cache_delete.delete = Mock()
        mock_tokens_delete.delete = Mock()
        self.mock_db.commit = Mock()
        
        # Test
        result = self.oauth_service.revoke_oauth_connection(100, 'discord')
        
        # Verify
        self.assertTrue(result)
        mock_cache_delete.delete.assert_called_once()
        mock_tokens_delete.delete.assert_called_once()
        self.mock_db.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()