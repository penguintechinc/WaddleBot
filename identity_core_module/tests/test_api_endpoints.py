"""
Unit tests for Identity API endpoints
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os
from datetime import datetime, timedelta

# Add the module path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestIdentityAPIEndpoints(unittest.TestCase):
    """Test cases for Identity API endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock py4web components
        self.mock_request = Mock()
        self.mock_response = Mock()
        self.mock_session = Mock()
        self.mock_db = Mock()
        self.mock_auth = Mock()
        self.mock_redis = Mock()
        
        # Mock database tables
        self.mock_db.auth_user = Mock()
        self.mock_db.platform_identities = Mock()
        self.mock_db.identity_verifications = Mock()
        self.mock_db.user_api_keys = Mock()
        self.mock_db.oauth_user_cache = Mock()
        
        # Mock services
        self.mock_platform_service = Mock()
        self.mock_verification_service = Mock()
        self.mock_identity_service = Mock()
    
    @patch('app.request')
    @patch('app.db')
    @patch('app.auth')
    def test_link_identity_success(self, mock_auth, mock_db, mock_request):
        """Test successful identity linking initiation"""
        # Setup request data
        mock_request.json = {
            'source_platform': 'discord',
            'target_platform': 'twitch',
            'target_username': 'testuser'
        }
        
        # Setup auth user
        mock_auth.user_id = 123
        
        # Setup existing source identity
        mock_source_identity = Mock()
        mock_source_identity.platform_username = 'discord_user'
        
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_source_identity
        mock_db.__call__.return_value = mock_query
        
        # Setup no existing target identity
        mock_target_query = Mock()
        mock_target_query.select.return_value.first.return_value = None
        
        # Setup pending verification query
        mock_pending_query = Mock()
        mock_pending_query.select.return_value.first.return_value = None
        
        mock_db.__call__.side_effect = [mock_query, mock_target_query, mock_pending_query]
        
        # Setup database insert and commit
        mock_db.identity_verifications.insert = Mock()
        mock_db.commit = Mock()
        
        # Mock verification service
        with patch('app.verification_service') as mock_verification_service:
            mock_verification_service.generate_code.return_value = 'ABC123'
            
            # Mock platform service
            with patch('app.platform_service') as mock_platform_service:
                # Import and test the function
                from app import link_identity
                
                # Execute
                with patch.object(mock_request, 'json', mock_request.json):
                    result = link_identity()
                
                # Verify
                self.assertTrue(result['success'])
                self.assertIn('Verification code sent', result['message'])
                mock_db.identity_verifications.insert.assert_called_once()
                mock_db.commit.assert_called_once()
    
    @patch('app.request')
    @patch('app.db')
    def test_link_identity_missing_data(self, mock_db, mock_request):
        """Test identity linking with missing data"""
        # Setup incomplete request data
        mock_request.json = {
            'source_platform': 'discord'
            # Missing target_platform and target_username
        }
        
        from app import link_identity
        
        # Execute and expect failure
        with self.assertRaises(Exception):  # Should abort with 400
            link_identity()
    
    @patch('app.request')
    @patch('app.db')
    def test_verify_identity_success(self, mock_db, mock_request):
        """Test successful identity verification"""
        # Setup request data
        mock_request.json = {
            'platform': 'twitch',
            'platform_id': '123456',
            'platform_username': 'testuser',
            'verification_code': 'ABC123'
        }
        
        # Setup pending verification
        mock_verification = Mock()
        mock_verification.user_id = 100
        mock_verification.update_record = Mock()
        
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_verification
        mock_db.__call__.return_value = mock_query
        
        # Setup no existing identity
        mock_existing_query = Mock()
        mock_existing_query.select.return_value.first.return_value = None
        
        # Setup user platform query
        mock_user_platform_query = Mock()
        mock_user_platform_query.select.return_value.first.return_value = None
        
        mock_db.__call__.side_effect = [mock_query, mock_existing_query, mock_user_platform_query]
        
        # Setup database operations
        mock_db.platform_identities.insert = Mock()
        mock_db.commit = Mock()
        
        # Setup user update
        mock_user = Mock()
        mock_user.primary_platform = None
        mock_user.update_record = Mock()
        mock_db.auth_user.__getitem__.return_value = mock_user
        
        # Mock Redis
        with patch('app.redis_client') as mock_redis:
            mock_redis.setex = Mock()
            
            from app import verify_identity
            
            # Execute
            result = verify_identity()
            
            # Verify
            self.assertTrue(result['success'])
            self.assertEqual(result['user_id'], 100)
            mock_db.platform_identities.insert.assert_called_once()
            mock_verification.update_record.assert_called_once()
            mock_user.update_record.assert_called_once()
    
    @patch('app.request')
    @patch('app.db')
    def test_verify_identity_invalid_code(self, mock_db, mock_request):
        """Test identity verification with invalid code"""
        # Setup request data
        mock_request.json = {
            'platform': 'twitch',
            'platform_id': '123456',
            'platform_username': 'testuser',
            'verification_code': 'INVALID'
        }
        
        # Setup no matching verification
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = None
        mock_db.__call__.return_value = mock_query
        
        from app import verify_identity
        
        # Execute and expect failure
        with self.assertRaises(Exception):  # Should abort with 400
            verify_identity()
    
    @patch('app.request')
    @patch('app.db')
    @patch('app.auth')
    def test_create_api_key_success(self, mock_auth, mock_db, mock_request):
        """Test successful API key creation"""
        # Setup request data
        mock_request.json = {
            'name': 'Test Key',
            'expires_in_days': 365
        }
        
        # Setup auth user
        mock_auth.user_id = 123
        
        # Setup active keys count
        mock_count_query = Mock()
        mock_count_query.count.return_value = 2  # Under limit
        mock_db.__call__.return_value = mock_count_query
        
        # Setup database insert
        mock_db.user_api_keys.insert.return_value = 456
        mock_db.commit = Mock()
        
        # Mock secrets
        with patch('app.secrets') as mock_secrets:
            mock_secrets.token_urlsafe.return_value = 'random_token'
            
            # Mock hashlib
            with patch('app.hashlib') as mock_hashlib:
                mock_hashlib.sha256.return_value.hexdigest.return_value = 'hashed_key'
                
                from app import create_api_key
                
                # Execute
                result = create_api_key()
                
                # Verify
                self.assertTrue(result['success'])
                self.assertEqual(result['key_id'], 456)
                self.assertIn('wbot_user_', result['api_key'])
                mock_db.user_api_keys.insert.assert_called_once()
    
    @patch('app.request')
    @patch('app.db')
    @patch('app.auth')
    def test_create_api_key_over_limit(self, mock_auth, mock_db, mock_request):
        """Test API key creation when over limit"""
        # Setup request data
        mock_request.json = {
            'name': 'Test Key'
        }
        
        # Setup auth user
        mock_auth.user_id = 123
        
        # Setup active keys count over limit
        mock_count_query = Mock()
        mock_count_query.count.return_value = 10  # Over limit
        mock_db.__call__.return_value = mock_count_query
        
        from app import create_api_key
        
        # Execute and expect failure
        with self.assertRaises(Exception):  # Should abort with 400
            create_api_key()
    
    @patch('app.db')
    @patch('app.auth')
    def test_list_api_keys_success(self, mock_auth, mock_db):
        """Test successful API key listing"""
        # Setup auth user
        mock_auth.user_id = 123
        
        # Setup API keys
        mock_key1 = Mock()
        mock_key1.id = 1
        mock_key1.name = 'Key 1'
        mock_key1.created_at = datetime.utcnow()
        mock_key1.expires_at = datetime.utcnow() + timedelta(days=365)
        mock_key1.last_used_at = None
        mock_key1.usage_count = 0
        
        mock_key2 = Mock()
        mock_key2.id = 2
        mock_key2.name = 'Key 2'
        mock_key2.created_at = datetime.utcnow()
        mock_key2.expires_at = None
        mock_key2.last_used_at = datetime.utcnow()
        mock_key2.usage_count = 5
        
        mock_query = Mock()
        mock_query.select.return_value = [mock_key1, mock_key2]
        mock_db.__call__.return_value = mock_query
        
        from app import list_api_keys
        
        # Execute
        result = list_api_keys()
        
        # Verify
        self.assertIn('api_keys', result)
        self.assertEqual(len(result['api_keys']), 2)
        self.assertEqual(result['api_keys'][0]['key_id'], 1)
        self.assertEqual(result['api_keys'][1]['usage_count'], 5)
    
    @patch('app.db')
    @patch('app.auth')
    def test_revoke_api_key_success(self, mock_auth, mock_db):
        """Test successful API key revocation"""
        # Setup auth user
        mock_auth.user_id = 123
        
        # Setup API key
        mock_api_key = Mock()
        mock_api_key.update_record = Mock()
        
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = mock_api_key
        mock_db.__call__.return_value = mock_query
        
        mock_db.commit = Mock()
        
        from app import revoke_api_key
        
        # Execute
        result = revoke_api_key(456)  # key_id = 456
        
        # Verify
        self.assertTrue(result['success'])
        mock_api_key.update_record.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch('app.db')
    @patch('app.auth')
    def test_revoke_api_key_not_found(self, mock_auth, mock_db):
        """Test API key revocation when key not found"""
        # Setup auth user
        mock_auth.user_id = 123
        
        # Setup no API key found
        mock_query = Mock()
        mock_query.select.return_value.first.return_value = None
        mock_db.__call__.return_value = mock_query
        
        from app import revoke_api_key
        
        # Execute and expect failure
        with self.assertRaises(Exception):  # Should abort with 404
            revoke_api_key(456)

if __name__ == '__main__':
    unittest.main()