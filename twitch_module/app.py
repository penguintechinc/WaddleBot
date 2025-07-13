"""
Main application file for the Twitch py4web module
"""

import os
import logging
from py4web import action, request, response, abort, redirect, Field
from py4web.core import Fixture

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the module components
from . import models
from .controllers import webhooks, api, auth

# Import database
from .models import db

@action("twitch")
@action("twitch/")
def index():
    """Main index page for the Twitch module"""
    return {
        "message": "WaddleBot Twitch Module",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "login": "/twitch/auth/login",
                "callback": "/twitch/auth/callback",
                "status": "/twitch/auth/status",
                "users": "/twitch/auth/users"
            },
            "api": {
                "user": "/twitch/api/user/<user_id>",
                "subscriptions": "/twitch/api/subscriptions",
                "channels": "/twitch/api/channels"
            },
            "webhooks": {
                "events": "/twitch/webhook",
                "list_events": "/twitch/events",
                "list_activities": "/twitch/activities"
            }
        }
    }

@action("twitch/health")
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.executesql("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": str(db.executesql("SELECT datetime('now')")[0][0])
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        response.status = 503
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@action("twitch/info")
def module_info():
    """Module information and statistics"""
    try:
        # Get database statistics
        stats = {
            "channels": db(db.twitch_channels).count(),
            "subscriptions": db(db.twitch_subscriptions).count(),
            "events": db(db.twitch_events).count(),
            "activities": db(db.twitch_activities).count(),
            "authenticated_users": db(db.twitch_tokens).count()
        }
        
        # Get recent activity
        recent_events = db(db.twitch_events).select(
            orderby=~db.twitch_events.created_at,
            limitby=(0, 5)
        )
        
        recent_activities = db(db.twitch_activities).select(
            orderby=~db.twitch_activities.created_at,
            limitby=(0, 5)
        )
        
        return {
            "module": "WaddleBot Twitch Module",
            "version": "1.0.0",
            "statistics": stats,
            "recent_events": [dict(event) for event in recent_events],
            "recent_activities": [dict(activity) for activity in recent_activities]
        }
        
    except Exception as e:
        logger.error(f"Error getting module info: {str(e)}")
        response.status = 500
        return {"error": str(e)}

# Initialize database tables if needed
def init_database():
    """Initialize database tables"""
    try:
        db.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

# Call initialization
init_database()