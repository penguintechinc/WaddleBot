"""
Spotify API Service
Handles Spotify authentication, search, and playback control
"""

import logging
import requests
import json
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs

logger = logging.getLogger(__name__)

class SpotifyService:
    """Service for interacting with Spotify API"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.client_id = config.SPOTIFY_CLIENT_ID
        self.client_secret = config.SPOTIFY_CLIENT_SECRET
        self.redirect_uri = config.SPOTIFY_REDIRECT_URI
        self.api_base = config.SPOTIFY_API_BASE_URL
        self.accounts_base = config.SPOTIFY_ACCOUNTS_BASE_URL
        
        # Create HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'WaddleBot/1.0 Spotify'
        })
    
    def get_auth_url(self, community_id: str, user_id: str) -> str:
        """Generate Spotify OAuth authorization URL"""
        state = json.dumps({
            'community_id': community_id,
            'user_id': user_id
        })
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'scope': self.config.SPOTIFY_SCOPES,
            'redirect_uri': self.redirect_uri,
            'state': state,
            'show_dialog': 'true'
        }
        
        return f"{self.accounts_base}/authorize?" + urlencode(params)
    
    def exchange_code_for_tokens(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access tokens"""
        try:
            # Create basic auth header
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(
                f"{self.accounts_base}/api/token",
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            # Calculate expiry time
            expires_at = datetime.utcnow() + timedelta(seconds=token_data['expires_in'])
            
            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'expires_at': expires_at,
                'scope': token_data.get('scope', '')
            }
            
        except Exception as e:
            logger.error(f"Token exchange failed: {str(e)}")
            return None
    
    def store_user_tokens(self, community_id: str, user_id: str, tokens: Dict):
        """Store user tokens in database"""
        try:
            self.db.spotify_tokens.update_or_insert(
                (self.db.spotify_tokens.community_id == community_id) &
                (self.db.spotify_tokens.user_id == user_id),
                community_id=community_id,
                user_id=user_id,
                access_token=tokens['access_token'],
                refresh_token=tokens['refresh_token'],
                expires_at=tokens['expires_at'],
                scope=tokens.get('scope', ''),
                updated_at=datetime.utcnow()
            )
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store tokens: {str(e)}")
            return False
    
    def get_user_tokens(self, community_id: str, user_id: str) -> Optional[Dict]:
        """Get user tokens from database"""
        try:
            token_record = self.db(
                (self.db.spotify_tokens.community_id == community_id) &
                (self.db.spotify_tokens.user_id == user_id)
            ).select().first()
            
            if not token_record:
                return None
            
            return {
                'access_token': token_record.access_token,
                'refresh_token': token_record.refresh_token,
                'expires_at': token_record.expires_at,
                'scope': token_record.scope
            }
            
        except Exception as e:
            logger.error(f"Failed to get tokens: {str(e)}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token"""
        try:
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            
            response = requests.post(
                f"{self.accounts_base}/api/token",
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()
            
            token_data = response.json()
            expires_at = datetime.utcnow() + timedelta(seconds=token_data['expires_in'])
            
            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token', refresh_token),
                'expires_at': expires_at,
                'scope': token_data.get('scope', '')
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return None
    
    def check_user_auth(self, community_id: str, user_id: str) -> bool:
        """Check if user has valid authentication"""
        tokens = self.get_user_tokens(community_id, user_id)
        if not tokens:
            return False
        
        # Check if token is about to expire
        if tokens['expires_at'] <= datetime.utcnow() + timedelta(minutes=5):
            # Try to refresh
            new_tokens = self.refresh_access_token(tokens['refresh_token'])
            if new_tokens:
                self.store_user_tokens(community_id, user_id, new_tokens)
                return True
            else:
                return False
        
        return True
    
    def _make_api_request(self, community_id: str, user_id: str, endpoint: str, method: str = 'GET', data: Dict = None) -> Optional[Dict]:
        """Make authenticated API request"""
        tokens = self.get_user_tokens(community_id, user_id)
        if not tokens:
            return None
        
        headers = {
            'Authorization': f'Bearer {tokens["access_token"]}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = self.session.get(
                    f"{self.api_base}/{endpoint}",
                    headers=headers,
                    timeout=self.config.REQUEST_TIMEOUT
                )
            elif method == 'POST':
                response = self.session.post(
                    f"{self.api_base}/{endpoint}",
                    headers=headers,
                    json=data,
                    timeout=self.config.REQUEST_TIMEOUT
                )
            elif method == 'PUT':
                response = self.session.put(
                    f"{self.api_base}/{endpoint}",
                    headers=headers,
                    json=data,
                    timeout=self.config.REQUEST_TIMEOUT
                )
            else:
                return None
            
            if response.status_code == 401:
                # Token expired, try to refresh
                new_tokens = self.refresh_access_token(tokens['refresh_token'])
                if new_tokens:
                    self.store_user_tokens(community_id, user_id, new_tokens)
                    headers['Authorization'] = f'Bearer {new_tokens["access_token"]}'
                    # Retry request
                    response = self.session.request(
                        method,
                        f"{self.api_base}/{endpoint}",
                        headers=headers,
                        json=data,
                        timeout=self.config.REQUEST_TIMEOUT
                    )
            
            if response.status_code == 204:
                return {"success": True}
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"API request failed: {endpoint} - {str(e)}")
            return None
    
    def search_tracks(self, community_id: str, user_id: str, query: str, limit: int = 10) -> List[Dict]:
        """Search for tracks"""
        try:
            params = {
                'q': query,
                'type': 'track',
                'limit': min(limit, self.config.MAX_SEARCH_RESULTS),
                'market': 'US'
            }
            
            endpoint = f"search?{urlencode(params)}"
            data = self._make_api_request(community_id, user_id, endpoint)
            
            if data and 'tracks' in data:
                return data['tracks']['items']
            
            return []
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def get_track_info(self, community_id: str, user_id: str, track_uri: str) -> Optional[Dict]:
        """Get track information"""
        try:
            track_id = self.extract_track_id(track_uri)
            if not track_id:
                return None
            
            endpoint = f"tracks/{track_id}"
            return self._make_api_request(community_id, user_id, endpoint)
            
        except Exception as e:
            logger.error(f"Get track info failed: {str(e)}")
            return None
    
    def play_track(self, community_id: str, user_id: str, track_uri: str) -> bool:
        """Play a track"""
        try:
            data = {
                'uris': [track_uri]
            }
            
            result = self._make_api_request(community_id, user_id, 'me/player/play', 'PUT', data)
            return result is not None
            
        except Exception as e:
            logger.error(f"Play track failed: {str(e)}")
            return False
    
    def get_current_playback(self, community_id: str, user_id: str) -> Optional[Dict]:
        """Get current playback state"""
        return self._make_api_request(community_id, user_id, 'me/player')
    
    def pause_playback(self, community_id: str, user_id: str) -> bool:
        """Pause playback"""
        result = self._make_api_request(community_id, user_id, 'me/player/pause', 'PUT')
        return result is not None
    
    def resume_playback(self, community_id: str, user_id: str) -> bool:
        """Resume playback"""
        result = self._make_api_request(community_id, user_id, 'me/player/play', 'PUT')
        return result is not None
    
    def skip_track(self, community_id: str, user_id: str) -> bool:
        """Skip to next track"""
        result = self._make_api_request(community_id, user_id, 'me/player/next', 'POST')
        return result is not None
    
    def get_devices(self, community_id: str, user_id: str) -> List[Dict]:
        """Get available devices"""
        try:
            data = self._make_api_request(community_id, user_id, 'me/player/devices')
            if data and 'devices' in data:
                return data['devices']
            return []
            
        except Exception as e:
            logger.error(f"Get devices failed: {str(e)}")
            return []
    
    def extract_track_id(self, track_ref: str) -> Optional[str]:
        """Extract track ID from URI or URL"""
        # Spotify URI: spotify:track:4uLU6hMCjMI75M1A2tKUQC
        if track_ref.startswith('spotify:track:'):
            return track_ref.split(':')[2]
        
        # Spotify URL: https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC
        if 'open.spotify.com/track/' in track_ref:
            try:
                parsed = urlparse(track_ref)
                track_id = parsed.path.split('/track/')[1].split('?')[0]
                return track_id
            except:
                pass
        
        # Already a track ID
        if len(track_ref) == 22:
            return track_ref
        
        return None
    
    def extract_uri(self, track_ref: str) -> Optional[str]:
        """Extract or convert to Spotify URI"""
        track_id = self.extract_track_id(track_ref)
        if track_id:
            return f"spotify:track:{track_id}"
        return None
    
    def refresh_expiring_tokens(self):
        """Refresh tokens that are about to expire"""
        try:
            # Get tokens expiring in the next 5 minutes
            expiry_threshold = datetime.utcnow() + timedelta(minutes=5)
            
            expiring_tokens = self.db(
                self.db.spotify_tokens.expires_at <= expiry_threshold
            ).select()
            
            for token in expiring_tokens:
                new_tokens = self.refresh_access_token(token.refresh_token)
                if new_tokens:
                    self.store_user_tokens(token.community_id, token.user_id, new_tokens)
                    logger.info(f"Refreshed token for {token.community_id}/{token.user_id}")
                else:
                    logger.warning(f"Failed to refresh token for {token.community_id}/{token.user_id}")
                    
        except Exception as e:
            logger.error(f"Token refresh batch failed: {str(e)}")
    
    def check_health(self) -> Dict:
        """Check Spotify API health"""
        try:
            # Simple request to check API availability
            response = requests.get(
                "https://api.spotify.com/v1/browse/categories",
                timeout=5
            )
            
            return {
                'status': 'healthy' if response.status_code in [200, 401] else 'unhealthy',
                'api_status': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }