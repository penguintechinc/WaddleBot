"""
Twitch webhook handlers for EventSub
Handles incoming webhook events from Twitch
"""

import json
import hmac
import hashlib
import logging
from datetime import datetime
from py4web import action, request, response, HTTP, Field
from py4web.utils.form import Form, FormStyleBulma

from ..models import db
from ..config import load_config, ACTIVITY_POINTS
from ..dataclasses import (
    TwitchWebhookEvent, FollowEvent, SubscribeEvent, CheerEvent, 
    RaidEvent, GiftSubscriptionEvent, ContextPayload, IdentityPayload,
    dataclass_to_dict
)
from .api import WaddleBotAPI

# Load configuration
twitch_config, waddlebot_config = load_config()

# Initialize WaddleBot API client
waddlebot_api = WaddleBotAPI(waddlebot_config)

logger = logging.getLogger(__name__)

def verify_twitch_signature(signature: str, body: bytes, secret: str) -> bool:
    """Verify Twitch webhook signature"""
    if not signature:
        return False
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Remove 'sha256=' prefix from signature
    signature = signature.replace('sha256=', '')
    
    return hmac.compare_digest(signature, expected_signature)

@action("twitch/webhook", method=["POST", "GET"])
def twitch_webhook():
    """
    Main webhook endpoint for Twitch EventSub
    Handles verification challenges and event notifications
    """
    try:
        # Handle GET request for webhook verification
        if request.method == "GET":
            challenge = request.query.get("hub.challenge")
            if challenge:
                return challenge
            else:
                raise HTTP(400, "Missing challenge parameter")
        
        # Handle POST request for event notifications
        if request.method == "POST":
            # Get headers
            signature = request.headers.get("Twitch-Eventsub-Message-Signature")
            message_id = request.headers.get("Twitch-Eventsub-Message-Id")
            message_timestamp = request.headers.get("Twitch-Eventsub-Message-Timestamp")
            message_type = request.headers.get("Twitch-Eventsub-Message-Type")
            
            # Get raw body for signature verification
            body = request.body.read()
            
            # Verify signature
            if not verify_twitch_signature(signature, body, twitch_config.webhook_secret):
                logger.warning(f"Invalid signature for message {message_id}")
                raise HTTP(403, "Invalid signature")
            
            # Parse JSON body
            try:
                event_data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in webhook for message {message_id}")
                raise HTTP(400, "Invalid JSON")
            
            # Handle different message types
            if message_type == "webhook_callback_verification":
                # Return challenge for verification
                return event_data.get("challenge", "")
            
            elif message_type == "notification":
                # Process the event
                return process_twitch_event(event_data, message_id)
            
            elif message_type == "revocation":
                # Handle subscription revocation
                return handle_subscription_revocation(event_data, message_id)
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                raise HTTP(400, f"Unknown message type: {message_type}")
                
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

def process_twitch_event(event_data: dict, message_id: str) -> str:
    """Process incoming Twitch event"""
    try:
        subscription = event_data.get("subscription", {})
        event = event_data.get("event", {})
        
        subscription_id = subscription.get("id")
        event_type = subscription.get("type")
        
        # Log the event
        event_id = db.twitch_events.insert(
            event_id=message_id,
            subscription_id=get_subscription_record_id(subscription_id),
            event_type=event_type,
            broadcaster_user_id=event.get("broadcaster_user_id"),
            broadcaster_user_name=event.get("broadcaster_user_name"),
            user_id=event.get("user_id"),
            user_name=event.get("user_name"),
            event_data=event,
            processed=False
        )
        
        # Process the specific event type
        activity_type = None
        activity_amount = 0
        user_name = event.get("user_name", "")
        
        if event_type == "channel.follow":
            activity_type = "follow"
            activity_amount = ACTIVITY_POINTS.get("follow", 10)
            
        elif event_type == "channel.subscribe":
            activity_type = "sub"
            activity_amount = ACTIVITY_POINTS.get("sub", 50)
            
        elif event_type == "channel.cheer":
            activity_type = "bits"
            activity_amount = event.get("bits", 0)
            
        elif event_type == "channel.raid":
            activity_type = "raid"
            activity_amount = ACTIVITY_POINTS.get("raid", 30)
            user_name = event.get("from_broadcaster_user_name", "")
            
        elif event_type == "channel.subscription.gift":
            activity_type = "subgift"
            activity_amount = ACTIVITY_POINTS.get("subgift", 60)
            
        # Create activity record if we have a valid activity type
        if activity_type and user_name:
            channel_record = get_channel_record(event.get("broadcaster_user_id"))
            
            activity_id = db.twitch_activities.insert(
                event_id=event_id,
                activity_type=activity_type,
                user_name=user_name,
                amount=activity_amount,
                message=f"{activity_type} activity for {user_name}",
                channel_id=channel_record.id if channel_record else None
            )
            
            # Send to WaddleBot context API
            if channel_record:
                process_activity_context(activity_id, user_name, activity_type, activity_amount)
        
        # Mark event as processed
        db.twitch_events[event_id] = dict(processed=True, processed_at=datetime.utcnow())
        db.commit()
        
        logger.info(f"Processed event {message_id} of type {event_type}")
        return "OK"
        
    except Exception as e:
        logger.error(f"Error processing event {message_id}: {str(e)}")
        return "ERROR"

def handle_subscription_revocation(event_data: dict, message_id: str) -> str:
    """Handle EventSub subscription revocation"""
    try:
        subscription = event_data.get("subscription", {})
        subscription_id = subscription.get("id")
        
        # Update subscription status in database
        subscription_record = db(db.twitch_subscriptions.subscription_id == subscription_id).select().first()
        if subscription_record:
            db.twitch_subscriptions[subscription_record.id] = dict(status="revoked")
            db.commit()
            logger.info(f"Subscription {subscription_id} revoked")
        
        return "OK"
        
    except Exception as e:
        logger.error(f"Error handling revocation {message_id}: {str(e)}")
        return "ERROR"

def get_subscription_record_id(subscription_id: str):
    """Get database record ID for subscription"""
    record = db(db.twitch_subscriptions.subscription_id == subscription_id).select().first()
    return record.id if record else None

def get_channel_record(broadcaster_user_id: str):
    """Get channel record from database"""
    return db(db.twitch_channels.broadcaster_id == broadcaster_user_id).select().first()

def process_activity_context(activity_id: int, user_name: str, activity_type: str, amount: int):
    """Process activity through WaddleBot context API"""
    try:
        # Get user context
        identity_payload = IdentityPayload(identity_name=user_name)
        context = waddlebot_api.get_context(dataclass_to_dict(identity_payload))
        
        if context:
            # Create context payload
            context_payload = ContextPayload(
                userid=context['identity_id'],
                activity=activity_type,
                amount=amount,
                text=f"{activity_type} activity for {user_name}",
                namespace=context['namespace_name'],
                namespaceid=context['namespace_id'],
                platform="Twitch"
            )
            
            # Send to reputation API (when ready)
            # response = waddlebot_api.send_reputation(dataclass_to_dict(context_payload))
            
            # Update activity record
            db.twitch_activities[activity_id] = dict(
                context_sent=True,
                context_response=context
            )
            db.commit()
            
            logger.info(f"Context processed for {user_name}")
        else:
            logger.warning(f"No context found for user {user_name}")
            
    except Exception as e:
        logger.error(f"Error processing context for {user_name}: {str(e)}")

@action("twitch/events")
@action("twitch/events/<int:page>")
def list_events(page=1):
    """List recent Twitch events"""
    events = db(db.twitch_events).select(
        orderby=~db.twitch_events.created_at,
        limitby=((page-1)*20, page*20)
    )
    
    return {"events": events}

@action("twitch/activities")
@action("twitch/activities/<int:page>") 
def list_activities(page=1):
    """List recent Twitch activities"""
    activities = db(db.twitch_activities).select(
        orderby=~db.twitch_activities.created_at,
        limitby=((page-1)*20, page*20)
    )
    
    return {"activities": activities}