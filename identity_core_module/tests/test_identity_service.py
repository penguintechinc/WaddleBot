"""
Unit tests for Identity Service
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta

# Add the module path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestIdentityService(unittest.TestCase):
    """Test cases for IdentityService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock database
        self.mock_db = Mock()
        self.mock_redis = Mock()
        
        # Mock database tables
        self.mock_db.auth_user = Mock()
        self.mock_db.platform_identities = Mock()
        self.mock_db.identity_verifications = Mock()
        
        # Import after mocking
        from services.identity_service import IdentityService
        self.identity_service = IdentityService(self.mock_db, self.mock_redis)
    
    def test_get_user_by_platform_cached(self):
        """Test getting user by platform with cache hit"""
        # Setup cache hit
        self.mock_redis.get.return_value = "123"
        
        # Setup database user
        mock_user = Mock()
        mock_user.id = 123
        mock_user.username = "testuser"
        self.mock_db.auth_user.__getitem__.return_value = mock_user
        
        # Test
        result = self.identity_service.get_user_by_platform("twitch", "twitch123")
        
        # Verify cache was checked
        self.mock_redis.get.assert_called_with("identity:twitch:twitch123")
        self.assertEqual(result, mock_user)
    
    def test_get_user_by_platform_database(self):
        """Test getting user by platform with database lookup"""
        # Setup cache miss
        self.mock_redis.get.return_value = None
        
        # Setup database identity
        mock_identity = Mock()
        mock_identity.user_id = 123
        mock_identity.platform = "twitch"
        mock_identity.platform_id = "twitch123"
        
        # Setup database query
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_identity
        self.mock_db.__call__.return_value = mock_query
        
        # Setup user
        mock_user = Mock()
        mock_user.id = 123
        self.mock_db.auth_user.__getitem__.return_value = mock_user
        
        # Test
        result = self.identity_service.get_user_by_platform("twitch", "twitch123")
        
        # Verify cache was set
        self.mock_redis.setex.assert_called()
        self.assertEqual(result, mock_user)
    
    def test_create_identity_link_new(self):
        """Test creating new identity link"""
        # Setup no existing identity
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = None
        self.mock_db.__call__.return_value = mock_query
        
        # Setup user platform query
        mock_user_query = Mock()
        mock_user_query.select.return_value.first.return_value = None
        
        # Setup insert
        self.mock_db.platform_identities.insert = Mock()
        self.mock_db.commit = Mock()
        
        # Setup user update
        mock_user = Mock()
        mock_user.primary_platform = None
        mock_user.update_record = Mock()
        self.mock_db.auth_user.__getitem__.return_value = mock_user
        
        # Test
        result = self.identity_service.create_identity_link(
            123, "twitch", "twitch123", "testuser"
        )
        
        # Verify
        self.assertTrue(result)
        self.mock_db.platform_identities.insert.assert_called()
        self.mock_db.commit.assert_called()
        mock_user.update_record.assert_called_with(primary_platform="twitch")
    
    def test_create_identity_link_existing_different_user(self):
        """Test creating identity link when platform already linked to different user"""
        # Setup existing identity for different user
        mock_identity = Mock()
        mock_identity.user_id = 456  # Different user
        
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_identity
        self.mock_db.__call__.return_value = mock_query
        
        # Test
        result = self.identity_service.create_identity_link(
            123, "twitch", "twitch123", "testuser"
        )
        
        # Verify failure
        self.assertFalse(result)
    
    def test_remove_identity_link_success(self):
        """Test successful identity link removal"""
        # Setup existing identity
        mock_identity = Mock()
        mock_identity.id = 1
        mock_identity.platform_id = "twitch123"
        
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_identity
        
        # Setup identity count (more than 1)
        mock_count_query = Mock()
        mock_count_query.count.return_value = 2
        
        self.mock_db.__call__.return_value = mock_query
        
        # Setup delete
        mock_delete_query = Mock()
        mock_delete_query.delete = Mock()
        
        # Test
        result = self.identity_service.remove_identity_link(123, "twitch")
        
        # Verify
        self.assertTrue(result)
        self.mock_redis.delete.assert_called_with("identity:twitch:twitch123")
    
    def test_remove_identity_link_last_identity(self):
        """Test removing identity link when it's the last one"""
        # Setup existing identity
        mock_identity = Mock()
        mock_identity.id = 1
        
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_identity
        
        # Setup identity count (only 1)
        mock_count_query = Mock()
        mock_count_query.count.return_value = 1
        
        self.mock_db.__call__.return_value = mock_query
        
        # Test
        result = self.identity_service.remove_identity_link(123, "twitch")
        
        # Verify failure (can't remove last identity)
        self.assertFalse(result)

class TestVerificationService(unittest.TestCase):
    """Test cases for VerificationService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_redis = Mock()
        
        # Import after mocking
        from services.verification_service import VerificationService
        self.verification_service = VerificationService(self.mock_redis)
    
    def test_generate_code(self):
        """Test verification code generation"""
        # Setup Redis to not have existing code
        self.mock_redis.exists.return_value = False
        self.mock_redis.setex = Mock()
        
        # Test
        code = self.verification_service.generate_code()
        
        # Verify
        self.assertEqual(len(code), 6)  # Default length
        self.assertTrue(code.isalnum())
        self.mock_redis.setex.assert_called()
    
    def test_validate_code_format_valid(self):
        """Test valid verification code format"""
        result = self.verification_service.validate_code_format("ABC123")
        self.assertTrue(result)
    
    def test_validate_code_format_invalid_length(self):
        """Test invalid verification code format - wrong length"""
        result = self.verification_service.validate_code_format("ABC")
        self.assertFalse(result)
    
    def test_validate_code_format_invalid_chars(self):
        """Test invalid verification code format - invalid characters"""
        result = self.verification_service.validate_code_format("ABC12!")
        self.assertFalse(result)
    
    def test_check_rate_limit_within_limit(self):
        """Test rate limiting within allowed requests"""
        self.mock_redis.incr.return_value = 5  # Under limit
        
        result = self.verification_service.check_rate_limit("123", "verify")
        
        self.assertTrue(result)
    
    def test_check_rate_limit_exceeded(self):
        """Test rate limiting when limit exceeded"""
        self.mock_redis.incr.return_value = 100  # Over limit
        
        result = self.verification_service.check_rate_limit("123", "verify")
        
        self.assertFalse(result)

class TestPlatformService(unittest.TestCase):
    """Test cases for PlatformService"""
    
    def setUp(self):
        """Set up test fixtures"""
        from services.platform_service import PlatformService
        self.platform_service = PlatformService()
    
    @patch('services.platform_service.requests.post')
    def test_send_twitch_whisper_success(self, mock_post):
        """Test successful Twitch whisper"""
        # Setup successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test
        result = self.platform_service._send_twitch_whisper(
            "http://api.test", "testuser", "test message"
        )
        
        # Verify
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('services.platform_service.requests.post')
    def test_send_twitch_whisper_failure(self, mock_post):
        """Test failed Twitch whisper"""
        # Setup failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Error"
        mock_post.return_value = mock_response
        
        # Test
        result = self.platform_service._send_twitch_whisper(
            "http://api.test", "testuser", "test message"
        )
        
        # Verify
        self.assertFalse(result)
    
    def test_format_verification_message(self):
        """Test verification message formatting"""
        message = self.platform_service._format_verification_message(
            "ABC123", "discord", "testuser"
        )
        
        self.assertIn("ABC123", message)
        self.assertIn("discord", message)
        self.assertIn("testuser", message)
        self.assertIn("!verify ABC123", message)

if __name__ == '__main__':
    # Run the tests
    unittest.main()