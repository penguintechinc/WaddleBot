"""
OAuth Service for handling platform authentication with py4web native OAuth2
"""

import logging
from datetime import datetime
from ..config import Config
from ..logging_config import log_event

logger = logging.getLogger(Config.MODULE_NAME)

class OAuthService:
    """Service for managing OAuth authentication and platform identity linking"""
    
    def __init__(self, db, redis_client, identity_service):
        self.db = db
        self.redis_client = redis_client
        self.identity_service = identity_service
    
    def handle_oauth_callback(self, provider, user_data, auth_user):
        """
        Handle successful OAuth callback and link platform identity
        
        This is called after py4web Auth successfully authenticates the user
        """
        try:
            # Extract platform-specific data
            platform_id = self._extract_platform_id(provider, user_data)
            username = self._extract_username(provider, user_data)
            
            if not platform_id or not username:
                logger.error(f"Missing platform data for {provider}: {user_data}")
                return False
            
            # Set primary platform if not already set
            if not auth_user.primary_platform:
                auth_user.update_record(primary_platform=provider)
                self.db.commit()
            
            # Create or update platform identity
            success = self.identity_service.create_identity_link(
                auth_user.id,
                provider,
                platform_id,
                username,
                verification_method="oauth"
            )
            
            if success:
                # Cache OAuth user data
                self._cache_oauth_user_data(auth_user.id, provider, user_data, platform_id, username)
                
                log_event("AUTH", "OAUTH", 
                         user_id=auth_user.id,
                         platform=provider,
                         action="oauth_identity_linked",
                         result="success")
                
                return True
            else:
                logger.error(f"Failed to create identity link for {provider} user {username}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling OAuth callback for {provider}: {e}")
            log_event("ERROR", "OAUTH", 
                     action="oauth_callback_handling_failed",
                     result="error",
                     details={"provider": provider, "error": str(e)})
            return False
    
    def _extract_platform_id(self, provider, user_data):
        """Extract platform-specific user ID"""
        if provider == 'discord':
            return user_data.get('id')
        elif provider == 'twitch':
            return user_data.get('id')
        elif provider == 'slack':
            return user_data.get('user', {}).get('id') if 'user' in user_data else user_data.get('id')
        return None
    
    def _extract_username(self, provider, user_data):
        """Extract platform-specific username"""
        if provider == 'discord':
            return user_data.get('username')
        elif provider == 'twitch':
            return user_data.get('login')
        elif provider == 'slack':
            return user_data.get('user', {}).get('name') if 'user' in user_data else user_data.get('name')
        return None
    
    def _cache_oauth_user_data(self, user_id, provider, user_data, platform_id, username):
        """Cache OAuth user data for future reference"""
        try:
            # Extract additional user info
            email = self._extract_email(provider, user_data)
            display_name = self._extract_display_name(provider, user_data)
            avatar_url = self._extract_avatar_url(provider, user_data)
            
            # Store in oauth_user_cache table
            cache_record = self.db((self.db.oauth_user_cache.user_id == user_id) &
                                 (self.db.oauth_user_cache.provider == provider)).select().first()
            
            if cache_record:
                cache_record.update_record(
                    provider_user_id=platform_id,
                    provider_username=username,
                    provider_email=email,
                    provider_display_name=display_name,
                    provider_avatar_url=avatar_url,
                    raw_user_data=user_data,
                    last_updated=datetime.utcnow()
                )
            else:
                self.db.oauth_user_cache.insert(
                    user_id=user_id,
                    provider=provider,
                    provider_user_id=platform_id,
                    provider_username=username,
                    provider_email=email,
                    provider_display_name=display_name,
                    provider_avatar_url=avatar_url,
                    raw_user_data=user_data,
                    last_updated=datetime.utcnow()
                )
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error caching OAuth user data: {e}")
    
    def _extract_email(self, provider, user_data):
        """Extract email from user data"""
        if provider == 'discord':
            return user_data.get('email', '')
        elif provider == 'twitch':
            return user_data.get('email', '')
        elif provider == 'slack':
            return user_data.get('user', {}).get('profile', {}).get('email', '') if 'user' in user_data else user_data.get('email', '')
        return ''
    
    def _extract_display_name(self, provider, user_data):
        """Extract display name from user data"""
        if provider == 'discord':
            return user_data.get('global_name') or user_data.get('username', '')
        elif provider == 'twitch':
            return user_data.get('display_name', '')
        elif provider == 'slack':
            if 'user' in user_data:
                profile = user_data.get('user', {}).get('profile', {})
                return profile.get('display_name') or profile.get('real_name', '')
            return user_data.get('name', '')
        return ''
    
    def _extract_avatar_url(self, provider, user_data):
        """Extract avatar URL from user data"""
        if provider == 'discord':
            user_id = user_data.get('id')
            avatar = user_data.get('avatar')
            if user_id and avatar:
                return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"
        elif provider == 'twitch':
            return user_data.get('profile_image_url', '')
        elif provider == 'slack':
            if 'user' in user_data:
                return user_data.get('user', {}).get('profile', {}).get('image_72', '')
            return user_data.get('image_72', '')
        return ''
    
    def get_oauth_user_cache(self, user_id, provider):
        """Get cached OAuth user data"""
        try:
            cache_record = self.db((self.db.oauth_user_cache.user_id == user_id) &
                                 (self.db.oauth_user_cache.provider == provider)).select().first()
            
            if cache_record:
                return {
                    'provider_user_id': cache_record.provider_user_id,
                    'provider_username': cache_record.provider_username,
                    'provider_email': cache_record.provider_email,
                    'provider_display_name': cache_record.provider_display_name,
                    'provider_avatar_url': cache_record.provider_avatar_url,
                    'raw_user_data': cache_record.raw_user_data,
                    'last_updated': cache_record.last_updated
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting OAuth user cache: {e}")
            return None
    
    def refresh_oauth_data(self, user_id, provider):
        """Refresh OAuth user data from provider API"""
        # This would be implemented to refresh user data from the provider
        # For now, it's a placeholder for future enhancement
        pass
    
    def revoke_oauth_connection(self, user_id, provider):
        """Revoke OAuth connection and remove cached data"""
        try:
            # Remove cached OAuth data
            self.db((self.db.oauth_user_cache.user_id == user_id) &
                   (self.db.oauth_user_cache.provider == provider)).delete()
            
            # Remove OAuth tokens if any
            self.db((self.db.oauth_tokens.user_id == user_id) &
                   (self.db.oauth_tokens.provider == provider)).delete()
            
            self.db.commit()
            
            log_event("AUTH", "OAUTH", 
                     user_id=user_id,
                     platform=provider,
                     action="oauth_connection_revoked",
                     result="success")
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking OAuth connection: {e}")
            return False