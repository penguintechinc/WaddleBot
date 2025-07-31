"""
Identity Service for core identity management operations
"""

import logging
from datetime import datetime, timedelta
from ..config import Config
from ..logging_config import log_event

logger = logging.getLogger(Config.MODULE_NAME)

class IdentityService:
    """Core service for identity management"""
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis_client = redis_client
    
    def get_user_by_platform(self, platform, platform_id, use_cache=True):
        """Get WaddleBot user by platform identity with caching"""
        try:
            # Check cache first
            if use_cache and self.redis_client:
                cache_key = f"identity:{platform}:{platform_id}"
                cached_user_id = self.redis_client.get(cache_key)
                if cached_user_id:
                    user = self.db.auth_user[int(cached_user_id)]
                    if user:
                        return user
            
            # Query database
            identity = self.db((self.db.platform_identities.platform == platform) &
                             (self.db.platform_identities.platform_id == str(platform_id)) &
                             (self.db.platform_identities.is_verified == True)).select().first()
            
            if not identity:
                return None
            
            user = self.db.auth_user[identity.user_id]
            if not user:
                return None
            
            # Update cache
            if self.redis_client:
                cache_key = f"identity:{platform}:{platform_id}"
                self.redis_client.setex(cache_key, Config.CACHE_TTL, user.id)
            
            return user
            
        except Exception as e:
            logger.error(f"Error getting user by platform: {e}")
            return None
    
    def get_platform_identities(self, user_id):
        """Get all platform identities for a user"""
        try:
            identities = self.db((self.db.platform_identities.user_id == user_id) &
                               (self.db.platform_identities.is_verified == True)).select()
            
            result = []
            for identity in identities:
                result.append({
                    'platform': identity.platform,
                    'platform_id': identity.platform_id,
                    'platform_username': identity.platform_username,
                    'verified_at': identity.verified_at,
                    'verification_method': identity.verification_method
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting platform identities: {e}")
            return []
    
    def create_identity_link(self, user_id, platform, platform_id, platform_username, 
                           verification_method='whisper'):
        """Create a new platform identity link"""
        try:
            # Check if already exists
            existing = self.db((self.db.platform_identities.platform == platform) &
                             (self.db.platform_identities.platform_id == platform_id) &
                             (self.db.platform_identities.is_verified == True)).select().first()
            
            if existing:
                if existing.user_id == user_id:
                    return True  # Already linked to this user
                else:
                    return False  # Linked to different user
            
            # Check if user already has this platform
            user_platform = self.db((self.db.platform_identities.user_id == user_id) &
                                  (self.db.platform_identities.platform == platform)).select().first()
            
            if user_platform:
                # Update existing record
                user_platform.update_record(
                    platform_id=platform_id,
                    platform_username=platform_username,
                    is_verified=True,
                    verified_at=datetime.utcnow(),
                    verification_method=verification_method
                )
            else:
                # Create new record
                self.db.platform_identities.insert(
                    user_id=user_id,
                    platform=platform,
                    platform_id=platform_id,
                    platform_username=platform_username,
                    is_verified=True,
                    verified_at=datetime.utcnow(),
                    verification_method=verification_method
                )
            
            self.db.commit()
            
            # Update cache
            if self.redis_client:
                cache_key = f"identity:{platform}:{platform_id}"
                self.redis_client.setex(cache_key, Config.CACHE_TTL, user_id)
            
            # Update primary platform if not set
            user = self.db.auth_user[user_id]
            if user and not user.primary_platform:
                user.update_record(primary_platform=platform)
                self.db.commit()
            
            log_event(
                "AUDIT", "IDENTITY",
                user_id=user_id,
                platform=platform,
                action="identity_linked",
                result="success",
                details={
                    "platform_username": platform_username,
                    "verification_method": verification_method
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating identity link: {e}")
            return False
    
    def remove_identity_link(self, user_id, platform):
        """Remove a platform identity link"""
        try:
            # Find the identity
            identity = self.db((self.db.platform_identities.user_id == user_id) &
                             (self.db.platform_identities.platform == platform)).select().first()
            
            if not identity:
                return False
            
            # Check if this is the last identity
            identity_count = self.db((self.db.platform_identities.user_id == user_id) &
                                   (self.db.platform_identities.is_verified == True)).count()
            
            if identity_count <= 1:
                return False  # Don't allow removing last identity
            
            # Remove from cache
            if self.redis_client and identity.platform_id:
                cache_key = f"identity:{platform}:{identity.platform_id}"
                self.redis_client.delete(cache_key)
            
            # Delete the identity
            self.db(self.db.platform_identities.id == identity.id).delete()
            self.db.commit()
            
            log_event(
                "AUDIT", "IDENTITY",
                user_id=user_id,
                platform=platform,
                action="identity_unlinked",
                result="success"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing identity link: {e}")
            return False
    
    def search_users(self, query, platform=None, limit=50):
        """Search for users by username or display name"""
        try:
            # Build query
            conditions = []
            
            # Search in auth_user
            user_query = (self.db.auth_user.username.contains(query)) | \
                        (self.db.auth_user.waddlebot_display_name.contains(query))
            
            users = self.db(user_query).select(limitby=(0, limit))
            
            # If platform specified, filter by platform identity
            if platform:
                platform_query = (self.db.platform_identities.platform == platform) & \
                               (self.db.platform_identities.platform_username.contains(query)) & \
                               (self.db.platform_identities.is_verified == True)
                
                platform_users = self.db(platform_query).select()
                platform_user_ids = [p.user_id for p in platform_users]
                
                # Combine results
                combined_user_ids = set([u.id for u in users] + platform_user_ids)
                users = self.db(self.db.auth_user.id.belongs(combined_user_ids)).select(limitby=(0, limit))
            
            result = []
            for user in users:
                result.append({
                    'user_id': user.id,
                    'username': user.username,
                    'display_name': user.waddlebot_display_name or user.username,
                    'primary_platform': user.primary_platform,
                    'reputation_score': user.reputation_score or 0
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    def get_identity_stats(self):
        """Get identity statistics"""
        try:
            stats = {
                'total_users': self.db(self.db.auth_user).count(),
                'verified_identities': self.db(self.db.platform_identities.is_verified == True).count(),
                'platforms': {},
                'multi_platform_users': 0,
                'recent_verifications': 0
            }
            
            # Platform breakdown
            for platform in ['twitch', 'discord', 'slack']:
                stats['platforms'][platform] = self.db(
                    (self.db.platform_identities.platform == platform) &
                    (self.db.platform_identities.is_verified == True)
                ).count()
            
            # Multi-platform users
            multi_platform = self.db.executesql("""
                SELECT COUNT(DISTINCT user_id) 
                FROM platform_identities 
                WHERE is_verified = true
                GROUP BY user_id 
                HAVING COUNT(DISTINCT platform) > 1
            """)
            stats['multi_platform_users'] = len(multi_platform) if multi_platform else 0
            
            # Recent verifications (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            stats['recent_verifications'] = self.db(
                (self.db.platform_identities.verified_at > yesterday) &
                (self.db.platform_identities.is_verified == True)
            ).count()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting identity stats: {e}")
            return {}
    
    def cleanup_expired_verifications(self):
        """Clean up expired verification requests"""
        try:
            expired = self.db(
                (self.db.identity_verifications.status == 'pending') &
                (self.db.identity_verifications.expires_at < datetime.utcnow())
            )
            
            count = expired.count()
            expired.update(status='expired')
            self.db.commit()
            
            if count > 0:
                log_event(
                    "SYSTEM", "CLEANUP",
                    action="expired_verifications_cleaned",
                    result="success",
                    details={"count": count}
                )
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired verifications: {e}")
            return 0