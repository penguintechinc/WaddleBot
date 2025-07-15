"""
Session management service for tracking interaction sessions
Uses Redis to store session data with sessionID as key and entityID as value
"""

import os
import uuid
import redis
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages session IDs and entity mapping using Redis"""
    
    def __init__(self):
        # Redis configuration
        self.redis_host = os.environ.get("REDIS_HOST", "localhost")
        self.redis_port = int(os.environ.get("REDIS_PORT", 6379))
        self.redis_password = os.environ.get("REDIS_PASSWORD")
        self.redis_db = int(os.environ.get("REDIS_DB", 0))
        
        # Session configuration
        self.session_ttl = int(os.environ.get("SESSION_TTL", 3600))  # 1 hour default
        self.session_prefix = os.environ.get("SESSION_PREFIX", "waddlebot:session:")
        
        # Initialize Redis connection
        self.redis_client = self._connect_redis()
    
    def _connect_redis(self) -> redis.Redis:
        """Connect to Redis server"""
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=self.redis_db,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10,
                retry_on_timeout=True
            )
            
            # Test connection
            client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    def generate_session_id(self) -> str:
        """Generate a new session ID"""
        return str(uuid.uuid4())
    
    def create_session(self, entity_id: str) -> str:
        """Create a new session for an entity"""
        try:
            session_id = self.generate_session_id()
            session_key = f"{self.session_prefix}{session_id}"
            
            # Store session data
            session_data = {
                "entity_id": entity_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "request_count": 0
            }
            
            # Store in Redis with TTL
            self.redis_client.hmset(session_key, session_data)
            self.redis_client.expire(session_key, self.session_ttl)
            
            logger.debug(f"Created session {session_id} for entity {entity_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID"""
        try:
            session_key = f"{self.session_prefix}{session_id}"
            session_data = self.redis_client.hgetall(session_key)
            
            if not session_data:
                logger.debug(f"Session {session_id} not found or expired")
                return None
            
            # Convert request_count back to int
            if 'request_count' in session_data:
                session_data['request_count'] = int(session_data['request_count'])
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {str(e)}")
            return None
    
    def get_entity_id(self, session_id: str) -> Optional[str]:
        """Get entity ID from session ID"""
        try:
            session_data = self.get_session(session_id)
            return session_data.get('entity_id') if session_data else None
            
        except Exception as e:
            logger.error(f"Error getting entity ID for session {session_id}: {str(e)}")
            return None
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update session activity timestamp and increment request count"""
        try:
            session_key = f"{self.session_prefix}{session_id}"
            
            # Check if session exists
            if not self.redis_client.exists(session_key):
                logger.debug(f"Session {session_id} not found for activity update")
                return False
            
            # Update activity timestamp and request count
            self.redis_client.hmset(session_key, {
                "last_activity": datetime.utcnow().isoformat()
            })
            self.redis_client.hincrby(session_key, "request_count", 1)
            
            # Extend TTL
            self.redis_client.expire(session_key, self.session_ttl)
            
            logger.debug(f"Updated activity for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating session activity {session_id}: {str(e)}")
            return False
    
    def validate_session(self, session_id: str, entity_id: str) -> bool:
        """Validate that session ID belongs to the given entity"""
        try:
            session_data = self.get_session(session_id)
            
            if not session_data:
                logger.debug(f"Session {session_id} not found for validation")
                return False
            
            is_valid = session_data.get('entity_id') == entity_id
            
            if not is_valid:
                logger.warning(f"Session {session_id} entity mismatch: expected {entity_id}, got {session_data.get('entity_id')}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating session {session_id}: {str(e)}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            session_key = f"{self.session_prefix}{session_id}"
            deleted = self.redis_client.delete(session_key)
            
            if deleted:
                logger.debug(f"Deleted session {session_id}")
                return True
            else:
                logger.debug(f"Session {session_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (called by background task)"""
        try:
            pattern = f"{self.session_prefix}*"
            expired_count = 0
            
            # Get all session keys
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                # Check if key still exists (might have expired)
                if not self.redis_client.exists(key):
                    expired_count += 1
            
            logger.info(f"Cleaned up {expired_count} expired sessions")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            pattern = f"{self.session_prefix}*"
            keys = self.redis_client.keys(pattern)
            
            total_sessions = len(keys)
            active_sessions = 0
            total_requests = 0
            
            for key in keys:
                if self.redis_client.exists(key):
                    active_sessions += 1
                    request_count = self.redis_client.hget(key, "request_count")
                    if request_count:
                        total_requests += int(request_count)
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_requests": total_requests,
                "average_requests_per_session": round(total_requests / max(active_sessions, 1), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {str(e)}")
            return {"error": str(e)}

# Global session manager instance
session_manager = SessionManager()