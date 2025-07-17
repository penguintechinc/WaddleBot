"""
Browser Source Core Module for WaddleBot
Handles all browser source displays (ticker, media, general) with WebSocket support
"""

import os
import json
import logging
import secrets
import asyncio
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from py4web import action, request, response, abort, URL, redirect
from py4web.utils.form import Form, FormStyleDefault
from py4web.core import Fixture, Template
from pydal import DAL
from yamo_auth import auth
import websocket_server

from .models import define_tables
from .config import Config
from .services.browser_source_service import BrowserSourceService
from .services.websocket_service import WebSocketService
from .services.router_service import RouterService

# Initialize configuration
config = Config()

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='[%(asctime)s] %(levelname)s browser_source:%(module)s:%(lineno)d %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
db = DAL(
    config.DATABASE_URL,
    folder=os.path.join(os.path.dirname(__file__), 'databases'),
    pool_size=20,
    migrate=True,
    fake_migrate_all=False
)

# Define tables
define_tables(db)

# Initialize services
executor = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)
browser_service = BrowserSourceService(config, db, executor)
websocket_service = WebSocketService(config, browser_service)
router_service = RouterService(config)

# Register module with router on startup
try:
    router_service.register_module()
    logger.info("SYSTEM module=browser_source event=startup status=SUCCESS")
except Exception as e:
    logger.error(f"SYSTEM module=browser_source event=startup status=FAILED error={str(e)}")

# Template loader
template = Template('templates')

@action("browser/source/display", method=["POST"])
@action.uses(db)
def receive_display_data():
    """Receive display data from router and distribute to connected browser sources"""
    try:
        data = request.json
        if not data:
            logger.error("AUDIT module=browser_source action=receive_display result=FAILED error=no_data")
            return {"error": "No data provided"}, 400

        # Extract required fields
        session_id = data.get('session_id')
        community_id = data.get('community_id')
        source_type = data.get('source_type')  # ticker, media, general
        display_data = data.get('display_data')
        
        if not all([session_id, community_id, source_type, display_data]):
            logger.error("AUDIT module=browser_source action=receive_display result=FAILED error=missing_fields")
            return {"error": "Missing required fields"}, 400

        logger.info(f"AUDIT module=browser_source action=receive_display community={community_id} type={source_type}")

        # Process different source types
        if source_type == "ticker":
            # Ticker display
            ticker_data = {
                "type": "ticker",
                "text": display_data.get('ticker_text', ''),
                "duration": display_data.get('ticker_duration', 10),
                "style": display_data.get('ticker_style', 'default'),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Queue ticker message
            browser_service.queue_ticker_message(community_id, ticker_data)
            
        elif source_type == "media":
            # Media display (music, video, images)
            media_data = {
                "type": "media",
                "media_type": display_data.get('media_type', 'image'),
                "media_url": display_data.get('media_url', ''),
                "media_data": display_data.get('media_data', {}),
                "duration": display_data.get('duration', 30),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to media browser source
            browser_service.send_media_update(community_id, media_data)
            
        elif source_type == "general":
            # General HTML/content display
            general_data = {
                "type": "general",
                "content": display_data.get('content', ''),
                "style": display_data.get('style', {}),
                "duration": display_data.get('duration', 0),  # 0 = permanent
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to general browser source
            browser_service.send_general_update(community_id, general_data)
            
        else:
            logger.error(f"Unknown source type: {source_type}")
            return {"error": f"Unknown source type: {source_type}"}, 400

        # Store in history
        db.browser_source_history.insert(
            community_id=community_id,
            source_type=source_type,
            content=json.dumps(display_data),
            session_id=session_id,
            created_at=datetime.utcnow()
        )
        db.commit()

        return {"status": "success", "session_id": session_id}

    except Exception as e:
        logger.error(f"ERROR module=browser_source action=receive_display error={str(e)} traceback={traceback.format_exc()}")
        return {"error": "Internal server error"}, 500

@action("browser/source/<community_token>/<source_type>", method=["GET"])
@action.uses(db, template)
def browser_source_display(community_token, source_type):
    """Browser source display endpoint for OBS"""
    try:
        # Validate source type
        if source_type not in ['ticker', 'media', 'general']:
            abort(404)
        
        # Look up community by token
        source = db(
            (db.browser_source_tokens.token == community_token) &
            (db.browser_source_tokens.source_type == source_type) &
            (db.browser_source_tokens.is_active == True)
        ).select().first()
        
        if not source:
            logger.warning(f"Invalid browser source token: {community_token}")
            abort(404)
        
        community_id = source.community_id
        
        # Generate WebSocket URL
        ws_url = f"ws://{request.environ.get('HTTP_HOST')}/ws/{community_token}/{source_type}"
        
        # Log access
        db.browser_source_access_log.insert(
            community_id=community_id,
            source_type=source_type,
            ip_address=request.environ.get('REMOTE_ADDR'),
            user_agent=request.environ.get('HTTP_USER_AGENT'),
            accessed_at=datetime.utcnow()
        )
        db.commit()
        
        # Return appropriate template
        if source_type == "ticker":
            return template(f'ticker.html', ws_url=ws_url, community_id=community_id)
        elif source_type == "media":
            return template(f'media.html', ws_url=ws_url, community_id=community_id)
        else:  # general
            return template(f'general.html', ws_url=ws_url, community_id=community_id)
            
    except Exception as e:
        logger.error(f"Browser source display error: {str(e)}")
        abort(500)

@action("browser/source/admin/tokens", method=["GET", "POST"])
@action.uses(db, auth)
def manage_tokens():
    """Manage browser source tokens for communities"""
    try:
        if request.method == "GET":
            # Get tokens for user's communities
            # This would integrate with community management
            return {"message": "Token management endpoint"}
        
        elif request.method == "POST":
            data = request.json
            community_id = data.get('community_id')
            
            # Verify user has permission for this community
            # This would check with router/community service
            
            # Generate tokens for all source types
            tokens = {}
            for source_type in ['ticker', 'media', 'general']:
                # Check if token already exists
                existing = db(
                    (db.browser_source_tokens.community_id == community_id) &
                    (db.browser_source_tokens.source_type == source_type)
                ).select().first()
                
                if existing:
                    tokens[source_type] = {
                        'token': existing.token,
                        'url': f"{config.BASE_URL}/browser/source/{existing.token}/{source_type}"
                    }
                else:
                    # Generate new token
                    token = secrets.token_urlsafe(32)
                    
                    db.browser_source_tokens.insert(
                        community_id=community_id,
                        source_type=source_type,
                        token=token,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    
                    tokens[source_type] = {
                        'token': token,
                        'url': f"{config.BASE_URL}/browser/source/{token}/{source_type}"
                    }
            
            db.commit()
            
            logger.info(f"AUDIT module=browser_source action=generate_tokens community={community_id} result=SUCCESS")
            return {"status": "success", "tokens": tokens}
            
    except Exception as e:
        logger.error(f"Token management error: {str(e)}")
        return {"error": "Failed to manage tokens"}, 500

@action("browser/source/health", method=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db.executesql("SELECT 1")
        
        # Get WebSocket stats
        ws_stats = websocket_service.get_stats()
        
        # Get queue stats
        queue_stats = browser_service.get_queue_stats()
        
        return {
            "status": "healthy",
            "module": "browser_source_core",
            "version": config.MODULE_VERSION,
            "websocket_connections": ws_stats,
            "queue_stats": queue_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}, 503

@action("browser/source/api/communities/<community_id>/urls", method=["GET"])
@action.uses(db)
def get_community_urls(community_id):
    """API endpoint to get browser source URLs for a community"""
    try:
        # This would verify permission through router service
        
        urls = {}
        tokens = db(
            (db.browser_source_tokens.community_id == community_id) &
            (db.browser_source_tokens.is_active == True)
        ).select()
        
        for token in tokens:
            urls[token.source_type] = {
                'url': f"{config.BASE_URL}/browser/source/{token.token}/{token.source_type}",
                'created_at': token.created_at.isoformat()
            }
        
        return {"status": "success", "urls": urls}
        
    except Exception as e:
        logger.error(f"Get URLs error: {str(e)}")
        return {"error": "Failed to get URLs"}, 500

# WebSocket endpoint handler
@action("ws/<community_token>/<source_type>", method=["GET"])
def websocket_endpoint(community_token, source_type):
    """WebSocket endpoint for real-time updates"""
    # This is handled by the WebSocket service
    websocket_service.handle_connection(request, community_token, source_type)

# Start background services
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
    
    def process_queues():
        """Process ticker queues and cleanup"""
        while True:
            try:
                browser_service.process_ticker_queues()
                browser_service.cleanup_old_data()
                time.sleep(1)  # Process every second
            except Exception as e:
                logger.error(f"Queue processing failed: {str(e)}")
                time.sleep(5)
    
    # Start WebSocket server
    websocket_service.start()
    
    # Start background threads
    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    
    queue_thread = threading.Thread(target=process_queues, daemon=True)
    queue_thread.start()