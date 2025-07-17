"""
YouTube Music Interaction Module for WaddleBot
Handles YouTube Music search, playback info, and now playing information
"""

import os
import json
import logging
import traceback
from datetime import datetime
from py4web import action, request, response, abort, Field
from py4web.utils.form import Form, FormStyleDefault
from py4web.core import Fixture
from pydal import DAL
from yamo_auth import auth

from .models import define_tables
from .config import Config
from .services.youtube_music_service import YouTubeMusicService
from .services.router_service import RouterService

# Initialize configuration
config = Config()

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='[%(asctime)s] %(levelname)s youtube_music:%(module)s:%(lineno)d %(message)s'
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
youtube_service = YouTubeMusicService(config)
router_service = RouterService(config)

# Register module with router on startup
try:
    router_service.register_module()
    logger.info("SYSTEM module=youtube_music event=startup status=SUCCESS")
except Exception as e:
    logger.error(f"SYSTEM module=youtube_music event=startup status=FAILED error={str(e)}")

@action("youtube/music/interaction", method=["POST"])
@action.uses(db)
def music_interaction():
    """Main interaction endpoint for YouTube Music commands"""
    try:
        data = request.json
        if not data:
            logger.error("AUDIT module=youtube_music action=interaction result=FAILED error=no_data")
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
            logger.error("AUDIT module=youtube_music action=interaction result=FAILED error=missing_fields")
            return {"error": "Missing required fields"}, 400

        logger.info(f"AUDIT module=youtube_music action=interaction community={community_id} user={user_id} command={command}")

        # Process command
        response_data = None
        
        if command == "!ytmusic" or command == "!youtube":
            if not args:
                response_data = {
                    "session_id": session_id,
                    "success": True,
                    "response_action": "chat",
                    "chat_message": "YouTube Music commands: !ytmusic search <query>, !ytmusic current, !ytmusic play <url/id>"
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
                        results = youtube_service.search_music(query, limit=5)
                        if results:
                            # Format search results
                            messages = ["YouTube Music Search Results:"]
                            for i, track in enumerate(results[:5], 1):
                                messages.append(f"{i}. {track['title']} - {track['artist']} ({track['duration']})")
                            
                            response_data = {
                                "session_id": session_id,
                                "success": True,
                                "response_action": "chat",
                                "chat_message": "\n".join(messages)
                            }
                            
                            # Store search results for quick access
                            db.youtube_search_cache.insert(
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
                    # Get track identifier (URL or search result number)
                    if len(args) < 2:
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": "Please provide a YouTube URL or search result number"
                        }
                    else:
                        track_ref = ' '.join(args[1:])
                        track_info = None
                        
                        # Check if it's a number (search result)
                        if track_ref.isdigit():
                            # Get from recent search cache
                            cache = db(
                                (db.youtube_search_cache.community_id == community_id) &
                                (db.youtube_search_cache.user_id == user_id)
                            ).select(orderby=~db.youtube_search_cache.created_at).first()
                            
                            if cache and cache.results:
                                results = json.loads(cache.results)
                                idx = int(track_ref) - 1
                                if 0 <= idx < len(results):
                                    track_info = results[idx]
                        else:
                            # It's a URL or video ID
                            track_info = youtube_service.get_track_info(track_ref)
                        
                        if track_info:
                            # Store as now playing
                            db.youtube_now_playing.update_or_insert(
                                (db.youtube_now_playing.community_id == community_id),
                                community_id=community_id,
                                video_id=track_info.get('video_id'),
                                title=track_info.get('title'),
                                artist=track_info.get('artist'),
                                album=track_info.get('album'),
                                duration=track_info.get('duration'),
                                thumbnail_url=track_info.get('thumbnail'),
                                requested_by=user_id,
                                started_at=datetime.utcnow()
                            )
                            db.commit()
                            
                            # Return HTML response for browser source - universal music format
                            html_content = f"""
                            <div class="music-display" data-service="youtube">
                                <img src="{track_info['thumbnail']}" alt="Album Art" class="album-cover" />
                                <div class="artist-name">{track_info['artist']}</div>
                                <div class="song-name">{track_info['title']}</div>
                            </div>
                            """
                            
                            response_data = {
                                "session_id": session_id,
                                "success": True,
                                "response_action": "general",
                                "content_type": "html",
                                "content": html_content,
                                "duration": 30,  # Display duration in seconds
                                "style": {
                                    "type": "media",
                                    "theme": "youtube"
                                }
                            }
                            
                            # Also send a chat message
                            router_service.send_response({
                                "session_id": session_id,
                                "success": True,
                                "response_action": "chat",
                                "chat_message": f"Now playing: {track_info['title']} by {track_info['artist']}"
                            })
                        else:
                            response_data = {
                                "session_id": session_id,
                                "success": False,
                                "response_action": "chat",
                                "chat_message": "Could not find or play that track"
                            }
                
                elif subcommand == "current" or subcommand == "nowplaying":
                    # Get current playing track
                    now_playing = db(
                        db.youtube_now_playing.community_id == community_id
                    ).select().first()
                    
                    if now_playing:
                        # Send HTML response for browser source - universal music format
                        html_content = f"""
                        <div class="music-display" data-service="youtube">
                            <img src="{now_playing.thumbnail_url}" alt="Album Art" class="album-cover" />
                            <div class="artist-name">{now_playing.artist}</div>
                            <div class="song-name">{now_playing.title}</div>
                        </div>
                        """
                        
                        response_data = {
                            "session_id": session_id,
                            "success": True,
                            "response_action": "general",
                            "content_type": "html",
                            "content": html_content,
                            "duration": 15,  # Display duration in seconds
                            "style": {
                                "type": "media",
                                "theme": "youtube"
                            }
                        }
                    else:
                        response_data = {
                            "session_id": session_id,
                            "success": False,
                            "response_action": "chat",
                            "chat_message": "No track is currently playing"
                        }
                
                elif subcommand == "stop":
                    # Clear now playing
                    db(db.youtube_now_playing.community_id == community_id).delete()
                    db.commit()
                    
                    response_data = {
                        "session_id": session_id,
                        "success": True,
                        "response_action": "chat",
                        "chat_message": "YouTube Music playback stopped"
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
            db.youtube_activity.insert(
                community_id=community_id,
                user_id=user_id,
                action=command,
                details=json.dumps({"args": args}),
                created_at=datetime.utcnow()
            )
            db.commit()
            
            logger.info(f"AUDIT module=youtube_music action=command_processed community={community_id} user={user_id} result=SUCCESS")
            return {"status": "success", "session_id": session_id}
        else:
            return {"error": "Failed to process command"}, 500

    except Exception as e:
        logger.error(f"ERROR module=youtube_music action=interaction error={str(e)} traceback={traceback.format_exc()}")
        
        # Send error response
        router_service.send_response({
            "session_id": session_id,
            "success": False,
            "response_action": "chat",
            "chat_message": "An error occurred processing your YouTube Music request"
        })
        
        return {"error": "Internal server error"}, 500

@action("youtube/music/health", method=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db.executesql("SELECT 1")
        
        # Check YouTube service
        youtube_status = youtube_service.check_health()
        
        return {
            "status": "healthy",
            "module": "youtube_music_interaction",
            "version": config.MODULE_VERSION,
            "youtube_service": youtube_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}, 503

@action("youtube/music/webhook", method=["POST"])
@action.uses(db)
def webhook():
    """Webhook endpoint for YouTube Music events"""
    try:
        data = request.json
        event_type = data.get('type')
        
        logger.info(f"AUDIT module=youtube_music action=webhook event={event_type}")
        
        # Process different webhook events
        if event_type == "track_ended":
            community_id = data.get('community_id')
            # Clear now playing for that community
            db(db.youtube_now_playing.community_id == community_id).delete()
            db.commit()
        
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        return {"error": "Failed to process webhook"}, 500

# Start background heartbeat
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
    
    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()