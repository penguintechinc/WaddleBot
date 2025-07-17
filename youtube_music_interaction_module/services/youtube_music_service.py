"""
YouTube Music API Service
Handles YouTube Music search, video info, and playback data
"""

import logging
import requests
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

class YouTubeMusicService:
    """Service for interacting with YouTube Music API"""
    
    def __init__(self, config):
        self.config = config
        self.api_key = config.YOUTUBE_API_KEY
        self.base_url = config.YOUTUBE_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'WaddleBot/1.0 YouTubeMusic'
        })
    
    def search_music(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for music on YouTube"""
        try:
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'videoCategoryId': self.config.YOUTUBE_MUSIC_CATEGORY_ID,
                'regionCode': self.config.YOUTUBE_REGION_CODE,
                'maxResults': min(limit, self.config.YOUTUBE_MAX_RESULTS),
                'key': self.api_key
            }
            
            response = self.session.get(
                f"{self.base_url}/search",
                params=params,
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                snippet = item['snippet']
                video_id = item['id']['videoId']
                
                # Get additional video details including duration
                video_info = self._get_video_details(video_id)
                
                results.append({
                    'video_id': video_id,
                    'title': snippet['title'],
                    'artist': snippet['channelTitle'],
                    'channel_id': snippet['channelId'],
                    'thumbnail': snippet['thumbnails']['medium']['url'],
                    'description': snippet['description'][:200],
                    'published_at': snippet['publishedAt'],
                    'duration': video_info.get('duration', 'Unknown'),
                    'view_count': video_info.get('view_count', 0)
                })
            
            logger.info(f"AUDIT module=youtube_music action=search query={query} results={len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"ERROR module=youtube_music action=search query={query} error={str(e)}")
            return []
    
    def get_track_info(self, video_ref: str) -> Optional[Dict]:
        """Get track information from video ID or URL"""
        try:
            video_id = self._extract_video_id(video_ref)
            if not video_id:
                return None
            
            params = {
                'part': 'snippet,contentDetails,statistics',
                'id': video_id,
                'key': self.api_key
            }
            
            response = self.session.get(
                f"{self.base_url}/videos",
                params=params,
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                return None
            
            item = items[0]
            snippet = item['snippet']
            details = item['contentDetails']
            stats = item.get('statistics', {})
            
            # Parse duration from ISO 8601
            duration = self._parse_duration(details['duration'])
            
            track_info = {
                'video_id': video_id,
                'title': snippet['title'],
                'artist': snippet['channelTitle'],
                'channel_id': snippet['channelId'],
                'album': snippet.get('albumName', ''),  # May not always be available
                'description': snippet['description'][:500],
                'thumbnail': snippet['thumbnails']['high']['url'],
                'duration': duration,
                'view_count': int(stats.get('viewCount', 0)),
                'like_count': int(stats.get('likeCount', 0)),
                'published_at': snippet['publishedAt'],
                'tags': snippet.get('tags', [])[:10]
            }
            
            logger.info(f"AUDIT module=youtube_music action=get_track video_id={video_id} title={snippet['title']}")
            return track_info
            
        except Exception as e:
            logger.error(f"ERROR module=youtube_music action=get_track video_ref={video_ref} error={str(e)}")
            return None
    
    def _get_video_details(self, video_id: str) -> Dict:
        """Get additional video details including duration"""
        try:
            params = {
                'part': 'contentDetails,statistics',
                'id': video_id,
                'key': self.api_key
            }
            
            response = self.session.get(
                f"{self.base_url}/videos",
                params=params,
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                return {}
            
            item = items[0]
            details = item['contentDetails']
            stats = item.get('statistics', {})
            
            return {
                'duration': self._parse_duration(details['duration']),
                'view_count': int(stats.get('viewCount', 0)),
                'like_count': int(stats.get('likeCount', 0))
            }
            
        except Exception as e:
            logger.error(f"ERROR module=youtube_music action=get_video_details video_id={video_id} error={str(e)}")
            return {}
    
    def _extract_video_id(self, video_ref: str) -> Optional[str]:
        """Extract video ID from URL or return as-is if already an ID"""
        # If it's already a video ID (11 characters)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', video_ref):
            return video_ref
        
        # Try to parse as URL
        try:
            parsed = urlparse(video_ref)
            
            # youtube.com/watch?v=VIDEO_ID
            if parsed.netloc in ['www.youtube.com', 'youtube.com']:
                query = parse_qs(parsed.query)
                return query.get('v', [None])[0]
            
            # youtu.be/VIDEO_ID
            elif parsed.netloc == 'youtu.be':
                return parsed.path.lstrip('/')
            
            # music.youtube.com/watch?v=VIDEO_ID
            elif parsed.netloc == 'music.youtube.com':
                query = parse_qs(parsed.query)
                return query.get('v', [None])[0]
            
        except Exception as e:
            logger.error(f"Failed to extract video ID: {str(e)}")
        
        return None
    
    def _parse_duration(self, iso_duration: str) -> str:
        """Parse ISO 8601 duration to human readable format"""
        # Example: PT4M13S -> 4:13
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
        if not match:
            return "Unknown"
        
        hours, minutes, seconds = match.groups()
        hours = int(hours or 0)
        minutes = int(minutes or 0)
        seconds = int(seconds or 0)
        
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def get_related_tracks(self, video_id: str, limit: int = 5) -> List[Dict]:
        """Get related tracks for autoplay"""
        try:
            params = {
                'part': 'snippet',
                'relatedToVideoId': video_id,
                'type': 'video',
                'videoCategoryId': self.config.YOUTUBE_MUSIC_CATEGORY_ID,
                'maxResults': limit,
                'key': self.api_key
            }
            
            response = self.session.get(
                f"{self.base_url}/search",
                params=params,
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                snippet = item['snippet']
                vid_id = item['id']['videoId']
                
                results.append({
                    'video_id': vid_id,
                    'title': snippet['title'],
                    'artist': snippet['channelTitle'],
                    'thumbnail': snippet['thumbnails']['default']['url']
                })
            
            return results
            
        except Exception as e:
            logger.error(f"ERROR module=youtube_music action=get_related video_id={video_id} error={str(e)}")
            return []
    
    def check_health(self) -> Dict:
        """Check YouTube API health"""
        try:
            # Simple API call to check connectivity
            params = {
                'part': 'snippet',
                'chart': 'mostPopular',
                'videoCategoryId': self.config.YOUTUBE_MUSIC_CATEGORY_ID,
                'maxResults': 1,
                'key': self.api_key
            }
            
            response = self.session.get(
                f"{self.base_url}/videos",
                params=params,
                timeout=5
            )
            
            return {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'api_status': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }