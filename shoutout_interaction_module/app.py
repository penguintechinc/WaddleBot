"""
Shoutout Interaction Module for WaddleBot
Handles user shoutouts with platform-specific information lookup and auto-shoutout functionality
"""

from py4web import action, request, response, DAL, Field, HTTP
from py4web.utils.cors import CORS
import json
import os
import logging
import requests
from datetime import datetime, timedelta
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite://storage.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

db = DAL(DATABASE_URL, pool_size=10, migrate=True)

# Define database tables
db.define_table(
    'shoutout_users',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True),
    Field('username', 'string', required=True),
    Field('platform', 'string', required=True),
    Field('profile_url', 'string'),
    Field('last_game', 'string'),
    Field('custom_message', 'text'),
    Field('additional_links', 'json'),
    Field('auto_shoutout', 'boolean', default=False),
    Field('shoutout_count', 'integer', default=0),
    Field('last_shoutout', 'datetime'),
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

db.define_table(
    'shoutout_history',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True),
    Field('username', 'string', required=True),
    Field('platform', 'string', required=True),
    Field('triggered_by', 'string', required=True),
    Field('auto_shoutout', 'boolean', default=False),
    Field('game_played', 'string'),
    Field('clip_url', 'string'),
    Field('response_data', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Create indexes
try:
    db.executesql('CREATE INDEX IF NOT EXISTS idx_shoutout_users_entity_username ON shoutout_users(entity_id, username);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_shoutout_users_auto ON shoutout_users(entity_id, auto_shoutout);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_shoutout_history_entity ON shoutout_history(entity_id, created_at);')
except Exception as e:
    logger.warning(f"Could not create indexes: {e}")

db.commit()

# CORS setup
CORS(response)

# Module configuration
MODULE_NAME = os.environ.get("MODULE_NAME", "shoutout_interaction")
MODULE_VERSION = os.environ.get("MODULE_VERSION", "1.0.0")
ROUTER_API_URL = os.environ.get("ROUTER_API_URL", "http://router:8000/router")

# Platform API configurations
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")
TWITCH_ACCESS_TOKEN = os.environ.get("TWITCH_ACCESS_TOKEN")

@action("health", method=["GET"])
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

@action("shoutout", method=["POST"])
def handle_shoutout():
    """Handle shoutout command"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        entity_id = data.get("entity_id")
        message_content = data.get("message_content", "")
        user_id = data.get("user_id")
        session_id = data.get("session_id")
        platform = data.get("platform", "twitch")
        
        if not all([entity_id, message_content, user_id, session_id]):
            raise HTTP(400, "Missing required fields")
        
        # Parse the command
        parts = message_content.strip().split()
        if len(parts) < 2:
            return {
                "success": False,
                "error": "Usage: !so <username> or !shoutout <username>"
            }
        
        target_username = parts[1]
        
        # Get or create user entry
        user_entry = get_or_create_user(entity_id, target_username, platform, user_id)
        
        # Get platform-specific user information
        user_info = get_platform_user_info(target_username, platform)
        
        # Update user entry with fresh information
        if user_info:
            update_data = {
                "profile_url": user_info.get("profile_url"),
                "last_game": user_info.get("last_game"),
                "updated_at": datetime.utcnow()
            }
            db.shoutout_users[user_entry.id] = update_data
            db.commit()
        
        # Generate shoutout response
        response_data = generate_shoutout_response(user_entry, user_info, platform)
        
        # Record shoutout history
        db.shoutout_history.insert(
            entity_id=entity_id,
            username=target_username,
            platform=platform,
            triggered_by=user_id,
            auto_shoutout=False,
            game_played=user_info.get("last_game") if user_info else None,
            clip_url=user_info.get("clip_url") if user_info else None,
            response_data=response_data
        )
        
        # Update shoutout count
        db.shoutout_users[user_entry.id] = dict(
            shoutout_count=user_entry.shoutout_count + 1,
            last_shoutout=datetime.utcnow()
        )
        db.commit()
        
        return {
            "success": True,
            **response_data
        }
    
    except Exception as e:
        logger.error(f"Error handling shoutout: {str(e)}")
        return {
            "success": False,
            "error": f"Error processing shoutout: {str(e)}"
        }

@action("shoutout/auto", method=["POST"])
def handle_auto_shoutout():
    """Handle auto-shoutout for users"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        entity_id = data.get("entity_id")
        username = data.get("username")
        platform = data.get("platform", "twitch")
        event_type = data.get("event_type", "follow")
        
        if not all([entity_id, username]):
            raise HTTP(400, "Missing required fields")
        
        # Check if user has auto-shoutout enabled
        user_entry = db(
            (db.shoutout_users.entity_id == entity_id) &
            (db.shoutout_users.username == username) &
            (db.shoutout_users.platform == platform) &
            (db.shoutout_users.auto_shoutout == True) &
            (db.shoutout_users.is_active == True)
        ).select().first()
        
        if not user_entry:
            return {
                "success": False,
                "error": "User not found or auto-shoutout not enabled"
            }
        
        # Check cooldown (don't auto-shoutout same user within 1 hour)
        if user_entry.last_shoutout:
            time_since_last = datetime.utcnow() - user_entry.last_shoutout
            if time_since_last < timedelta(hours=1):
                return {
                    "success": False,
                    "error": "Auto-shoutout cooldown active"
                }
        
        # Get platform-specific user information
        user_info = get_platform_user_info(username, platform)
        
        # Generate auto-shoutout response
        response_data = generate_auto_shoutout_response(user_entry, user_info, platform, event_type)
        
        # Record shoutout history
        db.shoutout_history.insert(
            entity_id=entity_id,
            username=username,
            platform=platform,
            triggered_by="system",
            auto_shoutout=True,
            game_played=user_info.get("last_game") if user_info else None,
            clip_url=user_info.get("clip_url") if user_info else None,
            response_data=response_data
        )
        
        # Update shoutout count
        db.shoutout_users[user_entry.id] = dict(
            shoutout_count=user_entry.shoutout_count + 1,
            last_shoutout=datetime.utcnow()
        )
        db.commit()
        
        return {
            "success": True,
            **response_data
        }
    
    except Exception as e:
        logger.error(f"Error handling auto-shoutout: {str(e)}")
        return {
            "success": False,
            "error": f"Error processing auto-shoutout: {str(e)}"
        }

@action("shoutout/manage", method=["POST"])
def manage_shoutout_user():
    """Manage shoutout user settings"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        entity_id = data.get("entity_id")
        username = data.get("username")
        platform = data.get("platform", "twitch")
        action_type = data.get("action")
        user_id = data.get("user_id")
        
        if not all([entity_id, username, action_type, user_id]):
            raise HTTP(400, "Missing required fields")
        
        if action_type == "enable_auto":
            # Enable auto-shoutout for user
            user_entry = get_or_create_user(entity_id, username, platform, user_id)
            db.shoutout_users[user_entry.id] = dict(auto_shoutout=True)
            db.commit()
            
            return {
                "success": True,
                "message": f"Auto-shoutout enabled for {username}"
            }
        
        elif action_type == "disable_auto":
            # Disable auto-shoutout for user
            user_entry = db(
                (db.shoutout_users.entity_id == entity_id) &
                (db.shoutout_users.username == username) &
                (db.shoutout_users.platform == platform)
            ).select().first()
            
            if user_entry:
                db.shoutout_users[user_entry.id] = dict(auto_shoutout=False)
                db.commit()
            
            return {
                "success": True,
                "message": f"Auto-shoutout disabled for {username}"
            }
        
        elif action_type == "set_message":
            # Set custom message for user
            custom_message = data.get("custom_message", "")
            user_entry = get_or_create_user(entity_id, username, platform, user_id)
            db.shoutout_users[user_entry.id] = dict(custom_message=custom_message)
            db.commit()
            
            return {
                "success": True,
                "message": f"Custom message set for {username}"
            }
        
        elif action_type == "add_links":
            # Add additional links for user
            additional_links = data.get("additional_links", {})
            user_entry = get_or_create_user(entity_id, username, platform, user_id)
            
            current_links = user_entry.additional_links or {}
            current_links.update(additional_links)
            
            db.shoutout_users[user_entry.id] = dict(additional_links=current_links)
            db.commit()
            
            return {
                "success": True,
                "message": f"Additional links added for {username}"
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action_type}"
            }
    
    except Exception as e:
        logger.error(f"Error managing shoutout user: {str(e)}")
        return {
            "success": False,
            "error": f"Error managing shoutout user: {str(e)}"
        }

@action("shoutout/list", method=["GET"])
def list_shoutout_users():
    """List all shoutout users for an entity"""
    try:
        entity_id = request.query.get("entity_id")
        if not entity_id:
            raise HTTP(400, "Missing entity_id parameter")
        
        users = db(
            (db.shoutout_users.entity_id == entity_id) &
            (db.shoutout_users.is_active == True)
        ).select(
            orderby=db.shoutout_users.username
        )
        
        user_list = []
        for user in users:
            user_data = dict(user)
            user_data["created_at"] = user.created_at.isoformat() if user.created_at else None
            user_data["updated_at"] = user.updated_at.isoformat() if user.updated_at else None
            user_data["last_shoutout"] = user.last_shoutout.isoformat() if user.last_shoutout else None
            user_list.append(user_data)
        
        return {
            "success": True,
            "users": user_list,
            "total": len(user_list)
        }
    
    except Exception as e:
        logger.error(f"Error listing shoutout users: {str(e)}")
        raise HTTP(500, f"Error listing shoutout users: {str(e)}")

def get_or_create_user(entity_id, username, platform, created_by):
    """Get or create a shoutout user entry"""
    user_entry = db(
        (db.shoutout_users.entity_id == entity_id) &
        (db.shoutout_users.username == username) &
        (db.shoutout_users.platform == platform)
    ).select().first()
    
    if not user_entry:
        user_id = db.shoutout_users.insert(
            entity_id=entity_id,
            username=username,
            platform=platform,
            created_by=created_by
        )
        user_entry = db.shoutout_users[user_id]
    
    return user_entry

def get_platform_user_info(username, platform):
    """Get platform-specific user information"""
    if platform == "twitch":
        return get_twitch_user_info(username)
    elif platform == "discord":
        return get_discord_user_info(username)
    elif platform == "slack":
        return get_slack_user_info(username)
    else:
        return None

def get_twitch_user_info(username):
    """Get Twitch user information including last game and clips"""
    try:
        if not TWITCH_CLIENT_ID or not TWITCH_ACCESS_TOKEN:
            logger.warning("Twitch API credentials not configured")
            return {
                "profile_url": f"https://twitch.tv/{username}",
                "last_game": None,
                "clip_url": None
            }
        
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {TWITCH_ACCESS_TOKEN}"
        }
        
        # Get user information
        user_response = requests.get(
            f"https://api.twitch.tv/helix/users?login={username}",
            headers=headers,
            timeout=10
        )
        
        if user_response.status_code != 200:
            logger.warning(f"Failed to get Twitch user info for {username}")
            return {
                "profile_url": f"https://twitch.tv/{username}",
                "last_game": None,
                "clip_url": None
            }
        
        user_data = user_response.json()
        if not user_data.get("data"):
            return {
                "profile_url": f"https://twitch.tv/{username}",
                "last_game": None,
                "clip_url": None
            }
        
        user_id = user_data["data"][0]["id"]
        
        # Get channel information for last game
        channel_response = requests.get(
            f"https://api.twitch.tv/helix/channels?broadcaster_id={user_id}",
            headers=headers,
            timeout=10
        )
        
        last_game = None
        if channel_response.status_code == 200:
            channel_data = channel_response.json()
            if channel_data.get("data"):
                last_game = channel_data["data"][0].get("game_name")
        
        # Get a random clip
        clip_url = get_random_twitch_clip(user_id, headers)
        
        return {
            "profile_url": f"https://twitch.tv/{username}",
            "last_game": last_game,
            "clip_url": clip_url
        }
    
    except Exception as e:
        logger.error(f"Error getting Twitch user info for {username}: {str(e)}")
        return {
            "profile_url": f"https://twitch.tv/{username}",
            "last_game": None,
            "clip_url": None
        }

def get_random_twitch_clip(user_id, headers):
    """Get a random Twitch clip for the user"""
    try:
        # Get clips from the last 7 days
        clips_response = requests.get(
            f"https://api.twitch.tv/helix/clips?broadcaster_id={user_id}&first=20&started_at={(datetime.utcnow() - timedelta(days=7)).isoformat()}Z",
            headers=headers,
            timeout=10
        )
        
        if clips_response.status_code == 200:
            clips_data = clips_response.json()
            if clips_data.get("data"):
                # Select a random clip
                clip = random.choice(clips_data["data"])
                return clip["url"]
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting random Twitch clip: {str(e)}")
        return None

def get_discord_user_info(username):
    """Get Discord user information"""
    # Discord usernames don't have public profiles like Twitch
    return {
        "profile_url": None,
        "last_game": None,
        "clip_url": None
    }

def get_slack_user_info(username):
    """Get Slack user information"""
    # Slack usernames don't have public profiles like Twitch
    return {
        "profile_url": None,
        "last_game": None,
        "clip_url": None
    }

def generate_shoutout_response(user_entry, user_info, platform):
    """Generate shoutout response based on user and platform information"""
    username = user_entry.username
    
    # Use custom message if available
    if user_entry.custom_message:
        message = user_entry.custom_message.format(
            username=username,
            game=user_info.get("last_game", "something awesome") if user_info else "something awesome"
        )
    else:
        # Generate default message
        if user_info and user_info.get("last_game"):
            message = f"Go check out {username}! They were last seen playing {user_info['last_game']}!"
        else:
            message = f"Go check out {username}! They're an awesome content creator!"
    
    # Add profile URL if available
    if user_info and user_info.get("profile_url"):
        message += f" {user_info['profile_url']}"
    
    # Add additional links if available
    if user_entry.additional_links:
        for link_name, link_url in user_entry.additional_links.items():
            message += f" | {link_name}: {link_url}"
    
    response_data = {
        "response_action": "chat",
        "response_data": {
            "message": message
        }
    }
    
    # Add full-screen media for Twitch clips
    if platform == "twitch" and user_info and user_info.get("clip_url"):
        response_data = {
            "response_action": "media",
            "response_data": {
                "media_type": "video",
                "media_url": user_info["clip_url"],
                "duration": 30,
                "title": f"Random clip from {username}",
                "description": message
            }
        }
    
    return response_data

def generate_auto_shoutout_response(user_entry, user_info, platform, event_type):
    """Generate auto-shoutout response"""
    username = user_entry.username
    
    # Generate event-specific message
    if event_type == "follow":
        message = f"Thanks for the follow, {username}! "
    elif event_type == "subscribe":
        message = f"Thanks for the sub, {username}! "
    elif event_type == "raid":
        message = f"Thanks for the raid, {username}! "
    else:
        message = f"Hey {username}! "
    
    # Add game information if available
    if user_info and user_info.get("last_game"):
        message += f"Make sure to check out their channel where they play {user_info['last_game']}!"
    else:
        message += "Make sure to check out their awesome content!"
    
    # Add profile URL if available
    if user_info and user_info.get("profile_url"):
        message += f" {user_info['profile_url']}"
    
    response_data = {
        "response_action": "chat",
        "response_data": {
            "message": message
        }
    }
    
    # Add full-screen media for Twitch clips
    if platform == "twitch" and user_info and user_info.get("clip_url"):
        response_data = {
            "response_action": "media",
            "response_data": {
                "media_type": "video",
                "media_url": user_info["clip_url"],
                "duration": 30,
                "title": f"Random clip from {username}",
                "description": message
            }
        }
    
    return response_data

if __name__ == "__main__":
    from py4web import start
    start(port=8011, host="0.0.0.0")