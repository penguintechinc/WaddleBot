"""
Verification Service for generating and managing verification codes
"""

import secrets
import string
import logging
import json
from datetime import datetime, timedelta
from ..config import Config
from ..logging_config import log_event

logger = logging.getLogger(Config.MODULE_NAME)

class VerificationService:
    """Service for managing verification codes and sessions"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.code_length = Config.VERIFICATION_CODE_LENGTH
        self.code_chars = string.ascii_uppercase + string.digits
        # Remove ambiguous characters
        self.code_chars = self.code_chars.replace('0', '').replace('O', '')
        self.code_chars = self.code_chars.replace('1', '').replace('I', '')
    
    def generate_code(self):
        """Generate a secure verification code"""
        code = ''.join(secrets.choice(self.code_chars) for _ in range(self.code_length))
        
        # Ensure code is unique in Redis
        if self.redis_client:
            attempts = 0
            while attempts < 10:
                key = f"verify:code:{code}"
                if not self.redis_client.exists(key):
                    # Reserve this code for the timeout period
                    self.redis_client.setex(
                        key, 
                        Config.VERIFICATION_TIMEOUT_MINUTES * 60,
                        "reserved"
                    )
                    break
                code = ''.join(secrets.choice(self.code_chars) for _ in range(self.code_length))
                attempts += 1
        
        logger.debug(f"Generated verification code: {code[:2]}***")
        return code
    
    def validate_code_format(self, code):
        """Validate verification code format"""
        if not code:
            return False
        
        code = code.upper().strip()
        if len(code) != self.code_length:
            return False
        
        # Check all characters are valid
        return all(c in self.code_chars for c in code)
    
    def store_verification_session(self, user_id, platform, code, metadata=None):
        """Store verification session in Redis for quick lookup"""
        if not self.redis_client:
            return
        
        session_data = {
            'user_id': user_id,
            'platform': platform,
            'code': code,
            'created_at': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        # Store by code for quick verification
        code_key = f"verify:session:{code}"
        self.redis_client.setex(
            code_key,
            Config.VERIFICATION_TIMEOUT_MINUTES * 60,
            json.dumps(session_data)
        )
        
        # Store by user for duplicate prevention
        user_key = f"verify:user:{user_id}:{platform}"
        self.redis_client.setex(
            user_key,
            Config.VERIFICATION_TIMEOUT_MINUTES * 60,
            code
        )
    
    def get_verification_session(self, code):
        """Retrieve verification session from Redis"""
        if not self.redis_client:
            return None
        
        code_key = f"verify:session:{code}"
        session_data = self.redis_client.get(code_key)
        
        if session_data:
            try:
                return json.loads(session_data)
            except:
                return None
        
        return None
    
    def check_rate_limit(self, user_id, action='verify'):
        """Check if user has exceeded rate limits"""
        if not self.redis_client:
            return True  # Allow if Redis not available
        
        key = f"ratelimit:{action}:{user_id}"
        current = self.redis_client.incr(key)
        
        if current == 1:
            # Set expiry on first increment
            self.redis_client.expire(key, Config.RATE_LIMIT_WINDOW)
        
        if current > Config.RATE_LIMIT_REQUESTS:
            log_event(
                "AUTHZ", "RATE_LIMIT",
                user_id=user_id,
                action=f"{action}_rate_limited",
                result="blocked"
            )
            return False
        
        return True
    
    def cleanup_expired_sessions(self):
        """Clean up expired verification sessions (called periodically)"""
        # Redis handles expiry automatically with TTL
        pass