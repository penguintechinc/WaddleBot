"""
Spotify Interaction Module for WaddleBot
Handles Spotify search, playback control, and now playing information
"""

import os
import json
import logging
import traceback
from datetime import datetime, timedelta
from py4web import action, request, response, abort, Field
from py4web.utils.form import Form, FormStyleDefault
from py4web.core import Fixture
from pydal import DAL
from yamo_auth import auth

from .models import define_tables
from .config import Config
from .services.spotify_service import SpotifyService
from .services.router_service import RouterService

# Initialize configuration
config = Config()

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='[%(asctime)s] %(levelname)s spotify:%(module)s:%(lineno)d %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
db = DAL(
    config.DATABASE_URL,
    folder=os.path.join(os.path.dirname(__file__), 'databases'),
    pool_size=10,
    migrate=True,
    fake_migrate_all=False
)

# Define tables
define_tables(db)

# Initialize services
spotify_service = SpotifyService(config, db)
router_service = RouterService(config)

# Register module with router on startup
try:
    router_service.register_module()
    logger.info("SYSTEM module=spotify event=startup status=SUCCESS")
except Exception as e:
    logger.error(f"SYSTEM module=spotify event=startup status=FAILED error={str(e)}")

@action("spotify/interaction", method=["POST"])
@action.uses(db)
def spotify_interaction():
    """Main interaction endpoint for Spotify commands"""
    try:
        data = request.json
        if not data:
            logger.error("AUDIT module=spotify action=interaction result=FAILED error=no_data")
            return {"error": "No data provided"}, 400

        # Extract required fields
        session_id = data.get('session_id')
        execution_id = data.get('execution_id')
        entity_id = data.get('entity_id')
        user_id = data.get('user_id')
        message = data.get('message', '')
        command = data.get('command', '')
        args = data.get('args', [])
        community_id = data.get('community_id')

        if not all([session_id, execution_id, entity_id, user_id]):
            logger.error("AUDIT module=spotify action=interaction result=FAILED error=missing_fields")
            return {"error": "Missing required fields"}, 400

        logger.info(f"AUDIT module=spotify action=interaction community={community_id} user={user_id} command={command}")

        # Process command
        response_data = None
        
        if command == "!spotify" or command == "!spot":
            if not args:
                response_data = {
                    "session_id": session_id,
                    "success": True,
                    "response_action": "chat",
                    "chat_message": "Spotify commands: !spotify search <query>, !spotify current, !spotify play <uri>, !spotify pause, !spotify resume, !spotify skip"
                }
            else:
                subcommand = args[0].lower()
                
                if subcommand == "search":
                    query = ' '.join(args[1:])
                    if not query:
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": "Please provide a search query"
                        }
                    else:
                        # Check if user has authenticated with Spotify
                        if not spotify_service.check_user_auth(community_id, user_id):
                            auth_url = spotify_service.get_auth_url(community_id, user_id)
                            response_data = {
                                "session_id": session_id,
                                "success": False,
                                "response_action": "chat",
                                "chat_message": f"Please authenticate with Spotify first: {auth_url}"
                            }
                        else:
                            results = spotify_service.search_tracks(community_id, user_id, query, limit=5)
                            if results:
                                # Format search results
                                messages = ["Spotify Search Results:"]
                                for i, track in enumerate(results[:5], 1):
                                    artists = ', '.join([a['name'] for a in track['artists']])
                                    duration = f"{track['duration_ms'] // 60000}:{(track['duration_ms'] % 60000) // 1000:02d}"
                                    messages.append(f"{i}. {track['name']} - {artists} ({duration})")
                                
                                response_data = {
                                    "session_id": session_id,
                                    "success": True,
                                    "response_action": "chat",
                                    "chat_message": "\n".join(messages)
                                }
                                
                                # Store search results for quick access
                                db.spotify_search_cache.insert(
                                    community_id=community_id,
                                    user_id=user_id,
                                    query=query,
                                    results=json.dumps(results),
                                    created_at=datetime.utcnow()
                                )
                                db.commit()
                            else:
                                response_data = {
                                    "session_id": session_id,
                                    "success": False,
                                    "response_action": "chat",
                                    "chat_message": "No results found for your search"
                                }
                
                elif subcommand == "play":
                    if not spotify_service.check_user_auth(community_id, user_id):
                        auth_url = spotify_service.get_auth_url(community_id, user_id)
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": f"Please authenticate with Spotify first: {auth_url}"
                        }
                    else:
                        # Get track reference (URI or search result number)
                        if len(args) < 2:
                            response_data = {
                                "session_id": session_id,
                                "success": False,
                                "response_action": "chat",
                                "chat_message": "Please provide a Spotify URI or search result number"
                            }
                        else:
                            track_ref = ' '.join(args[1:])
                            track_uri = None
                            
                            # Check if it's a number (search result)
                            if track_ref.isdigit():
                                # Get from recent search cache
                                cache = db(
                                    (db.spotify_search_cache.community_id == community_id) &
                                    (db.spotify_search_cache.user_id == user_id)
                                ).select(orderby=~db.spotify_search_cache.created_at).first()
                                
                                if cache and cache.results:
                                    results = json.loads(cache.results)
                                    idx = int(track_ref) - 1
                                    if 0 <= idx < len(results):
                                        track_uri = results[idx]['uri']
                            else:
                                # It's a URI or URL
                                track_uri = spotify_service.extract_uri(track_ref)
                            
                            if track_uri:
                                success = spotify_service.play_track(community_id, user_id, track_uri)
                                if success:
                                    # Get track info for display
                                    track_info = spotify_service.get_track_info(community_id, user_id, track_uri)
                                    if track_info:
                                        artists = ', '.join([a['name'] for a in track_info['artists']])
                                        
                                        # Store as now playing
                                        db.spotify_now_playing.update_or_insert(
                                            (db.spotify_now_playing.community_id == community_id),
                                            community_id=community_id,
                                            track_uri=track_uri,
                                            track_name=track_info['name'],
                                            artists=artists,
                                            album=track_info['album']['name'],
                                            duration_ms=track_info['duration_ms'],
                                            album_art_url=track_info['album']['images'][0]['url'] if track_info['album']['images'] else None,
                                            requested_by=user_id,
                                            started_at=datetime.utcnow()
                                        )
                                        db.commit()
                                        
                                        # Return HTML response for browser source - universal music format
                                        html_content = f"""
                                        <div class="music-display" data-service="spotify">
                                            <img src="{track_info['album']['images'][0]['url'] if track_info['album']['images'] else ''}" alt="Album Art" class="album-cover" />
                                            <div class="artist-name">{artists}</div>
                                            <div class="song-name">{track_info['name']}</div>
                                        </div>
                                        """
                                        
                                        response_data = {
                                            "session_id": session_id,
                                            "success": True,
                                            "response_action": "general",
                                            "content_type": "html",
                                            "content": html_content,
                                            "duration": 30,
                                            "style": {
                                                "type": "media",
                                                "theme": "spotify"
                                            }
                                        }
                                        
                                        # Also send a ticker message
                                        router_service.send_response({
                                            "session_id": session_id,
                                            "success": True,
                                            "response_action": "ticker",
                                            "ticker_text": f"🎵 Now playing on Spotify: {track_info['name']} by {artists}",
                                            "ticker_duration": 10
                                        })
                                else:
                                    response_data = {
                                        "session_id": session_id,
                                        "success": False,
                                        "response_action": "chat",
                                        "chat_message": "Failed to play track. Make sure Spotify is active on a device."
                                    }
                            else:
                                response_data = {
                                    "session_id": session_id,
                                    "success": False,
                                    "response_action": "chat",
                                    "chat_message": "Invalid track reference"
                                }
                
                elif subcommand == "current" or subcommand == "nowplaying":
                    if not spotify_service.check_user_auth(community_id, user_id):
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": "No Spotify authentication found"
                        }
                    else:
                        current = spotify_service.get_current_playback(community_id, user_id)
                        if current and current.get('is_playing'):
                            track = current['item']
                            artists = ', '.join([a['name'] for a in track['artists']])
                            progress = current['progress_ms'] // 1000
                            duration = track['duration_ms'] // 1000
                            
                            # Return HTML response for browser source - universal music format
                            html_content = f"""
                            <div class="music-display" data-service="spotify">
                                <img src="{track['album']['images'][0]['url'] if track['album']['images'] else ''}" alt="Album Art" class="album-cover" />
                                <div class="artist-name">{artists}</div>
                                <div class="song-name">{track['name']}</div>
                            </div>
                            """
                            
                            response_data = {
                                "session_id": session_id,
                                "success": True,
                                "response_action": "general",
                                "content_type": "html",
                                "content": html_content,
                                "duration": 15,
                                "style": {
                                    "type": "media",
                                    "theme": "spotify"
                                }
                            }
                        else:
                            response_data = {
                                "session_id": session_id,
                                "success": False,
                                "response_action": "chat",
                                "chat_message": "No track is currently playing on Spotify"
                            }
                
                elif subcommand == "pause":
                    if spotify_service.check_user_auth(community_id, user_id):
                        success = spotify_service.pause_playback(community_id, user_id)
                        response_data = {
                            "session_id": session_id,
                            "success": success,
                            "response_action": "chat",
                            "chat_message": "Spotify playback paused" if success else "Failed to pause playback"
                        }
                    else:
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": "No Spotify authentication found"
                        }
                
                elif subcommand == "resume" or subcommand == "unpause":
                    if spotify_service.check_user_auth(community_id, user_id):
                        success = spotify_service.resume_playback(community_id, user_id)
                        response_data = {
                            "session_id": session_id,
                            "success": success,
                            "response_action": "chat",
                            "chat_message": "Spotify playback resumed" if success else "Failed to resume playback"
                        }
                    else:
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": "No Spotify authentication found"
                        }
                
                elif subcommand == "skip" or subcommand == "next":
                    if spotify_service.check_user_auth(community_id, user_id):
                        success = spotify_service.skip_track(community_id, user_id)
                        response_data = {
                            "session_id": session_id,
                            "success": success,
                            "response_action": "chat",
                            "chat_message": "Skipped to next track" if success else "Failed to skip track"
                        }
                    else:
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": "No Spotify authentication found"
                        }
                
                elif subcommand == "devices":
                    if spotify_service.check_user_auth(community_id, user_id):
                        devices = spotify_service.get_devices(community_id, user_id)
                        if devices:
                            device_list = ["Available Spotify devices:"]
                            for i, device in enumerate(devices, 1):
                                active = " (active)" if device['is_active'] else ""
                                device_list.append(f"{i}. {device['name']} - {device['type']}{active}")
                            response_data = {
                                "session_id": session_id,
                                "success": True,
                                "response_action": "chat",
                                "chat_message": "\n".join(device_list)
                            }
                        else:
                            response_data = {
                                "session_id": session_id,
                                "success": False,
                                "response_action": "chat",
                                "chat_message": "No Spotify devices found"
                            }
                    else:
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": "No Spotify authentication found"
                        }
                
                else:
                    response_data = {
                        "session_id": session_id,
                        "success": False,
                        "response_action": "chat",
                        "chat_message": f"Unknown subcommand: {subcommand}"
                    }

        # Send response back to router
        if response_data:
            router_service.send_response(response_data)
            
            # Log activity
            db.spotify_activity.insert(
                community_id=community_id,
                user_id=user_id,
                action=command,
                details=json.dumps({"args": args}),
                created_at=datetime.utcnow()
            )
            db.commit()
            
            logger.info(f"AUDIT module=spotify action=command_processed community={community_id} user={user_id} result=SUCCESS")
            return {"status": "success", "session_id": session_id}
        else:
            return {"error": "Failed to process command"}, 500

    except Exception as e:
        logger.error(f"ERROR module=spotify action=interaction error={str(e)} traceback={traceback.format_exc()}")
        
        # Send error response
        router_service.send_response({
            "session_id": session_id,
            "success": False,
            "response_action": "chat",
            "chat_message": "An error occurred processing your Spotify request"
        })
        
        return {"error": "Internal server error"}, 500

@action("spotify/auth/callback", method=["GET"])
@action.uses(db)
def spotify_auth_callback():
    """Spotify OAuth callback endpoint"""
    try:
        code = request.query.get('code')
        state = request.query.get('state')
        error = request.query.get('error')
        
        if error:
            logger.error(f"Spotify auth error: {error}")
            return f"Authentication failed: {error}"
        
        if not code or not state:
            return "Missing authorization code or state"
        
        # Decode state to get community_id and user_id
        try:
            state_data = json.loads(state)
            community_id = state_data['community_id']
            user_id = state_data['user_id']
        except:
            return "Invalid state parameter"
        
        # Exchange code for tokens
        tokens = spotify_service.exchange_code_for_tokens(code)
        if tokens:
            # Store tokens
            spotify_service.store_user_tokens(community_id, user_id, tokens)
            
            logger.info(f"AUDIT module=spotify action=auth_success community={community_id} user={user_id}")
            return "Spotify authentication successful! You can now use Spotify commands."
        else:
            return "Failed to authenticate with Spotify"
            
    except Exception as e:
        logger.error(f"Spotify auth callback error: {str(e)}")
        return "Authentication error"

@action("spotify/health", method=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db.executesql("SELECT 1")
        
        # Check Spotify service
        spotify_status = spotify_service.check_health()
        
        return {
            "status": "healthy",
            "module": "spotify_interaction",
            "version": config.MODULE_VERSION,
            "spotify_service": spotify_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}, 503

# Start background heartbeat and token refresh
if __name__ != "__main__":
    import threading
    import time
    
    def heartbeat():
        while True:
            try:
                router_service.send_heartbeat()
                time.sleep(30)
            except Exception as e:
                logger.error(f"Heartbeat failed: {str(e)}")
                time.sleep(60)
    
    def refresh_tokens():
        while True:
            try:
                # Refresh tokens that are about to expire
                spotify_service.refresh_expiring_tokens()
                time.sleep(1800)  # Check every 30 minutes
            except Exception as e:
                logger.error(f"Token refresh failed: {str(e)}")
                time.sleep(300)
    
    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    
    refresh_thread = threading.Thread(target=refresh_tokens, daemon=True)
    refresh_thread.start()