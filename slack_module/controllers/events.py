"""
Slack event handlers using py4web and Slack SDK
Handles incoming events from Slack Event API
"""

import json
import hmac
import hashlib
import logging
from datetime import datetime
from py4web import action, request, response, HTTP

from ..models import db
from ..config import load_config, ACTIVITY_POINTS, MONITORED_EVENTS
from ..dataclasses import (
    SlackEvent, SlackMessage, SlackReaction, SlackUser, SlackChannel,
    ContextPayload, IdentityPayload, dataclass_to_dict
)
from ..services.core_api import core_api

# Load configuration
slack_config, waddlebot_config = load_config()

logger = logging.getLogger(__name__)

def verify_slack_signature(signature: str, timestamp: str, body: bytes) -> bool:
    """Verify Slack request signature"""
    if not signature or not timestamp:
        return False
    
    # Create signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_signature = 'v0=' + hmac.new(
        slack_config.signing_secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@action("slack/events", method=["POST"])
def slack_events():
    """
    Main event endpoint for Slack Event API
    Handles URL verification and event notifications
    """
    try:
        # Verify request signature
        signature = request.headers.get("X-Slack-Signature")
        timestamp = request.headers.get("X-Slack-Request-Timestamp")
        body = request.body.read()
        
        if not verify_slack_signature(signature, timestamp, body):
            logger.warning("Invalid Slack signature")
            raise HTTP(403, "Invalid signature")
        
        # Parse JSON body
        try:
            event_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in Slack event")
            raise HTTP(400, "Invalid JSON")
        
        # Handle URL verification challenge
        if event_data.get("type") == "url_verification":
            return {"challenge": event_data.get("challenge", "")}
        
        # Handle event callbacks
        elif event_data.get("type") == "event_callback":
            return process_slack_event(event_data)
        
        else:
            logger.warning(f"Unknown event type: {event_data.get('type')}")
            raise HTTP(400, f"Unknown event type: {event_data.get('type')}")
            
    except Exception as e:
        logger.error(f"Error processing Slack event: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

def process_slack_event(event_data: dict) -> str:
    """Process incoming Slack event"""
    try:
        event = event_data.get("event", {})
        team_id = event_data.get("team_id")
        event_type = event.get("type")
        event_id = event_data.get("event_id", f"slack_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}")
        
        # Check if this team is monitored
        if not is_monitored_team(team_id):
            logger.info(f"Team {team_id} not monitored, ignoring event")
            return "OK"
        
        # Skip bot messages unless it's a specific bot we care about
        if event.get("bot_id") and event.get("subtype") != "bot_message":
            return "OK"
        
        # Log the event
        event_record_id = log_slack_event(
            event_id=event_id,
            event_type=event_type,
            team_id=team_id,
            channel_id=event.get("channel"),
            user_id=event.get("user"),
            event_data=event
        )
        
        # Process specific event types
        activity_type = None
        activity_amount = 0
        user_id = event.get("user", "")
        user_name = get_user_name(user_id, team_id)
        
        if event_type == "message" and not event.get("subtype"):
            activity_type = "message"
            activity_amount = ACTIVITY_POINTS.get("message", 5)
            
            # Check for thread message
            if event.get("thread_ts"):
                activity_type = "thread_message"
                activity_amount = ACTIVITY_POINTS.get("thread_message", 6)
        
        elif event_type == "reaction_added":
            activity_type = "reaction"
            activity_amount = ACTIVITY_POINTS.get("reaction", 3)
            user_id = event.get("user", "")
            
        elif event_type == "member_joined_channel":
            activity_type = "member_joined_channel"
            activity_amount = ACTIVITY_POINTS.get("member_joined_channel", 10)
            user_id = event.get("user", "")
            
        elif event_type == "file_shared":
            activity_type = "file_share"
            activity_amount = ACTIVITY_POINTS.get("file_share", 15)
            user_id = event.get("user_id", "")
            
        elif event_type == "app_mention":
            activity_type = "app_mention"
            activity_amount = ACTIVITY_POINTS.get("app_mention", 8)
            
        elif event_type == "pin_added":
            activity_type = "pin_added"
            activity_amount = ACTIVITY_POINTS.get("pin_added", 10)
            
        # Create activity record if we have a valid activity type
        if activity_type and user_id and user_name:
            team_record = get_team_record(team_id)
            channel_record = get_channel_record(event.get("channel"))
            
            activity_id = db.slack_activities.insert(
                event_id=event_record_id,
                activity_type=activity_type,
                user_id=user_id,
                user_name=user_name,
                amount=activity_amount,
                message=f"{activity_type} activity for {user_name}",
                team_id=team_record.id if team_record else None,
                channel_id=channel_record.id if channel_record else None
            )
            
            # Send to WaddleBot context API
            if team_record:
                process_activity_context(activity_id, user_name, activity_type, activity_amount)
        
        # Mark event as processed
        if event_record_id:
            db.slack_events[event_record_id] = dict(processed=True, processed_at=datetime.utcnow())
            db.commit()
        
        logger.info(f"Processed Slack event {event_id} of type {event_type}")
        return "OK"
        
    except Exception as e:
        logger.error(f"Error processing Slack event: {str(e)}")
        return "ERROR"

def is_monitored_team(team_id: str) -> bool:
    """Check if a team is being monitored"""
    if not team_id:
        return False
    return db(db.slack_teams.team_id == team_id).count() > 0

def get_team_record(team_id: str):
    """Get team record from database"""
    return db(db.slack_teams.team_id == team_id).select().first()

def get_channel_record(channel_id: str):
    """Get channel record from database"""
    if not channel_id:
        return None
    return db(db.slack_channels.channel_id == channel_id).select().first()

def get_user_name(user_id: str, team_id: str) -> str:
    """Get user display name"""
    if not user_id:
        return ""
    
    # Try to get from cache first
    user_record = db(
        (db.slack_users.user_id == user_id) & 
        (db.slack_users.team_id == get_team_record(team_id).id if get_team_record(team_id) else None)
    ).select().first()
    
    if user_record:
        return user_record.display_name or user_record.real_name or user_record.username
    
    # TODO: Fetch from Slack API if not in cache
    return f"User-{user_id}"

def log_slack_event(event_id: str, event_type: str, team_id: str = None, 
                   channel_id: str = None, user_id: str = None, event_data: dict = None) -> int:
    """Log Slack event to database"""
    try:
        # Get database references
        team_record = None
        channel_record = None
        
        if team_id:
            team_record = get_team_record(team_id)
        
        if channel_id:
            channel_record = get_channel_record(channel_id)
        
        # Insert event
        record_id = db.slack_events.insert(
            event_id=event_id,
            event_type=event_type,
            team_id=team_record.id if team_record else None,
            channel_id=channel_record.id if channel_record else None,
            user_id=user_id,
            user_name=get_user_name(user_id, team_id) if user_id else None,
            event_data=event_data or {},
            processed=False,
            event_timestamp=event_data.get("ts", "") if event_data else ""
        )
        
        db.commit()
        return record_id
        
    except Exception as e:
        logger.error(f"Error logging Slack event: {str(e)}")
        return None

def process_activity_context(activity_id: int, user_name: str, activity_type: str, amount: int):
    """Process activity through WaddleBot context API"""
    try:
        # Get user context
        identity_payload = IdentityPayload(identity_name=user_name)
        context = core_api.get_context(dataclass_to_dict(identity_payload))
        
        if context:
            # Create context payload
            context_payload = ContextPayload(
                userid=context['identity_id'],
                activity=activity_type,
                amount=amount,
                text=f"{activity_type} activity for {user_name}",
                namespace=context['namespace_name'],
                namespaceid=context['namespace_id'],
                platform="Slack"
            )
            
            # Send to reputation API
            success = core_api.send_reputation(dataclass_to_dict(context_payload))
            
            # Update activity record
            db.slack_activities[activity_id] = dict(
                context_sent=success,
                context_response=context
            )
            db.commit()
            
            logger.info(f"Context processed for {user_name}")
        else:
            logger.warning(f"No context found for user {user_name}")
            
    except Exception as e:
        logger.error(f"Error processing context for {user_name}: {str(e)}")

@action("slack/slash", method=["POST"])
def slack_slash_commands():
    """Handle Slack slash commands"""
    try:
        # Verify request signature
        signature = request.headers.get("X-Slack-Signature")
        timestamp = request.headers.get("X-Slack-Request-Timestamp")
        body = request.body.read()
        
        if not verify_slack_signature(signature, timestamp, body):
            logger.warning("Invalid Slack signature for slash command")
            raise HTTP(403, "Invalid signature")
        
        # Parse form data
        form_data = dict(request.forms)
        
        command = form_data.get("command", "")
        text = form_data.get("text", "")
        user_id = form_data.get("user_id", "")
        user_name = form_data.get("user_name", "")
        team_id = form_data.get("team_id", "")
        channel_id = form_data.get("channel_id", "")
        
        # Check if team is monitored
        if not is_monitored_team(team_id):
            return {"text": "This workspace is not configured for WaddleBot."}
        
        # Log slash command usage
        log_slack_event(
            event_id=f"slash_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            event_type="slash_command",
            team_id=team_id,
            channel_id=channel_id,
            user_id=user_id,
            event_data={
                "command": command,
                "text": text,
                "user_name": user_name
            }
        )
        
        # Process basic commands
        if command == "/waddlebot":
            return handle_waddlebot_command(text, user_name, team_id)
        
        # Default response
        return {"text": f"Unknown command: {command}"}
        
    except Exception as e:
        logger.error(f"Error processing slash command: {str(e)}")
        return {"text": "Sorry, there was an error processing your command."}

def handle_waddlebot_command(text: str, user_name: str, team_id: str) -> dict:
    """Handle WaddleBot slash command"""
    args = text.strip().split() if text else []
    
    if not args or args[0] == "help":
        return {
            "text": "WaddleBot Commands:",
            "attachments": [
                {
                    "color": "good",
                    "fields": [
                        {"title": "/waddlebot help", "value": "Show this help message", "short": True},
                        {"title": "/waddlebot status", "value": "Show bot status", "short": True},
                        {"title": "/waddlebot points", "value": "Show your activity points", "short": True}
                    ]
                }
            ]
        }
    
    elif args[0] == "status":
        return {
            "text": f"WaddleBot is active and monitoring this workspace. Hello {user_name}!"
        }
    
    elif args[0] == "points":
        # Get user's recent activity
        team_record = get_team_record(team_id)
        if team_record:
            recent_activities = db(
                (db.slack_activities.user_name == user_name) &
                (db.slack_activities.team_id == team_record.id)
            ).select(
                orderby=~db.slack_activities.created_at,
                limitby=(0, 5)
            )
            
            total_points = sum(activity.amount for activity in recent_activities)
            
            return {
                "text": f"Your recent activity points: {total_points}",
                "attachments": [
                    {
                        "color": "good",
                        "fields": [
                            {
                                "title": activity.activity_type,
                                "value": f"{activity.amount} points",
                                "short": True
                            }
                            for activity in recent_activities
                        ]
                    }
                ]
            }
        else:
            return {"text": "Unable to retrieve your points at this time."}
    
    else:
        return {"text": f"Unknown command: {args[0]}. Use `/waddlebot help` for available commands."}

@action("slack/events/list")
@action("slack/events/list/<int:page>")
def list_events(page=1):
    """List recent Slack events"""
    events = db(db.slack_events).select(
        orderby=~db.slack_events.created_at,
        limitby=((page-1)*20, page*20)
    )
    
    return {"events": [dict(event) for event in events]}

@action("slack/activities/list")
@action("slack/activities/list/<int:page>")
def list_activities(page=1):
    """List recent Slack activities"""
    activities = db(db.slack_activities).select(
        orderby=~db.slack_activities.created_at,
        limitby=((page-1)*20, page*20)
    )
    
    return {"activities": [dict(activity) for activity in activities]}