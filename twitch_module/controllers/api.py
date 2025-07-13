"""
Twitch API connection handlers
Manages Twitch API interactions, token management, and subscriptions
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from py4web import action, request, response, HTTP, redirect, URL

from ..models import db
from ..config import load_config
from ..dataclasses import TwitchUser, TwitchToken, TwitchSubscription, dataclass_to_dict

# Load configuration
twitch_config, waddlebot_config = load_config()

logger = logging.getLogger(__name__)

class TwitchAPI:
    """Twitch API client"""
    
    def __init__(self):
        self.base_url = twitch_config.api_base_url
        self.auth_url = twitch_config.auth_base_url
        self.client_id = twitch_config.app_id
        self.client_secret = twitch_config.app_secret
        
    def get_app_access_token(self) -> str:
        """Get application access token"""
        url = f"{self.auth_url}/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data["access_token"]
    
    def get_user_info(self, access_token: str, user_id: str = None) -> Optional[TwitchUser]:
        """Get user information"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": self.client_id
        }
        
        params = {}
        if user_id:
            params["id"] = user_id
            
        response = requests.get(f"{self.base_url}/users", headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data["data"]:
            user_data = data["data"][0]
            return TwitchUser(**user_data)
        return None
    
    def refresh_token(self, refresh_token: str) -> TwitchToken:
        """Refresh access token"""
        url = f"{self.auth_url}/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        return TwitchToken(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", refresh_token),
            expires_in=token_data["expires_in"],
            scope=token_data["scope"]
        )
    
    def create_eventsub_subscription(self, access_token: str, event_type: str, condition: dict) -> TwitchSubscription:
        """Create EventSub subscription"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": self.client_id,
            "Content-Type": "application/json"
        }
        
        data = {
            "type": event_type,
            "version": "1",
            "condition": condition,
            "transport": {
                "method": "webhook",
                "callback": twitch_config.webhook_callback_url,
                "secret": twitch_config.webhook_secret
            }
        }
        
        response = requests.post(f"{self.base_url}/eventsub/subscriptions", 
                                headers=headers, json=data)
        response.raise_for_status()
        
        subscription_data = response.json()["data"][0]
        return TwitchSubscription(**subscription_data)
    
    def get_eventsub_subscriptions(self, access_token: str) -> List[TwitchSubscription]:
        """Get all EventSub subscriptions"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": self.client_id
        }
        
        response = requests.get(f"{self.base_url}/eventsub/subscriptions", headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return [TwitchSubscription(**sub) for sub in data["data"]]
    
    def delete_eventsub_subscription(self, access_token: str, subscription_id: str) -> bool:
        """Delete EventSub subscription"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": self.client_id
        }
        
        params = {"id": subscription_id}
        response = requests.delete(f"{self.base_url}/eventsub/subscriptions", 
                                  headers=headers, params=params)
        return response.status_code == 204

class WaddleBotAPI:
    """WaddleBot API client"""
    
    def __init__(self, config):
        self.context_url = config.context_api_url
        self.reputation_url = config.reputation_api_url
        self.gateway_url = config.gateway_activate_url
    
    def get_context(self, identity_payload: dict) -> Optional[dict]:
        """Get user context from WaddleBot API"""
        try:
            response = requests.post(self.context_url, json=identity_payload)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data") if data else None
            
        except requests.RequestException as e:
            logger.error(f"Error getting context: {str(e)}")
            return None
    
    def send_reputation(self, context_payload: dict) -> bool:
        """Send reputation data to WaddleBot API"""
        try:
            response = requests.post(self.reputation_url, json=context_payload)
            response.raise_for_status()
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error sending reputation: {str(e)}")
            return False
    
    def activate_gateway(self, activation_key: str) -> dict:
        """Activate gateway through WaddleBot API"""
        try:
            response = requests.post(self.gateway_url, json={"activation_key": activation_key})
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Error activating gateway: {str(e)}")
            return {"error": str(e)}

# Initialize API clients
twitch_api = TwitchAPI()
waddlebot_api = WaddleBotAPI(waddlebot_config)

@action("twitch/api/user/<user_id>")
def get_user(user_id: str):
    """Get Twitch user information"""
    try:
        # Get app access token for API calls
        access_token = twitch_api.get_app_access_token()
        user = twitch_api.get_user_info(access_token, user_id)
        
        if user:
            return {"user": dataclass_to_dict(user)}
        else:
            raise HTTP(404, "User not found")
            
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTP(500, f"Error: {str(e)}")

@action("twitch/api/subscriptions")
def manage_subscriptions():
    """Manage EventSub subscriptions"""
    if request.method == "GET":
        return list_subscriptions()
    elif request.method == "POST":
        return create_subscription()
    elif request.method == "DELETE":
        return delete_subscription()

def list_subscriptions():
    """List all EventSub subscriptions"""
    try:
        # Get app access token
        access_token = twitch_api.get_app_access_token()
        subscriptions = twitch_api.get_eventsub_subscriptions(access_token)
        
        return {"subscriptions": [dataclass_to_dict(sub) for sub in subscriptions]}
        
    except Exception as e:
        logger.error(f"Error listing subscriptions: {str(e)}")
        raise HTTP(500, f"Error: {str(e)}")

def create_subscription():
    """Create new EventSub subscription"""
    try:
        data = request.json
        event_type = data.get("type")
        condition = data.get("condition")
        
        if not event_type or not condition:
            raise HTTP(400, "Missing type or condition")
        
        # Get app access token
        access_token = twitch_api.get_app_access_token()
        subscription = twitch_api.create_eventsub_subscription(access_token, event_type, condition)
        
        # Save to database
        channel_id = condition.get("broadcaster_user_id")
        channel_record = db(db.twitch_channels.broadcaster_id == channel_id).select().first()
        
        db.twitch_subscriptions.insert(
            subscription_id=subscription.id,
            channel_id=channel_record.id if channel_record else None,
            event_type=event_type,
            status=subscription.status,
            cost=subscription.cost
        )
        db.commit()
        
        return {"subscription": dataclass_to_dict(subscription)}
        
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTP(500, f"Error: {str(e)}")

def delete_subscription():
    """Delete EventSub subscription"""
    try:
        subscription_id = request.json.get("id")
        if not subscription_id:
            raise HTTP(400, "Missing subscription ID")
        
        # Get app access token
        access_token = twitch_api.get_app_access_token()
        success = twitch_api.delete_eventsub_subscription(access_token, subscription_id)
        
        if success:
            # Update database
            db(db.twitch_subscriptions.subscription_id == subscription_id).update(status="deleted")
            db.commit()
            return {"success": True}
        else:
            raise HTTP(400, "Failed to delete subscription")
            
    except Exception as e:
        logger.error(f"Error deleting subscription: {str(e)}")
        raise HTTP(500, f"Error: {str(e)}")

@action("twitch/api/channels")
def manage_channels():
    """Manage monitored channels"""
    if request.method == "GET":
        return list_channels()
    elif request.method == "POST":
        return add_channel()

def list_channels():
    """List all monitored channels"""
    channels = db(db.twitch_channels).select()
    return {"channels": [dict(row) for row in channels]}

def add_channel():
    """Add new channel to monitor"""
    try:
        data = request.json
        channel_name = data.get("channel_name")
        gateway_id = data.get("gateway_id")
        
        if not channel_name:
            raise HTTP(400, "Missing channel name")
        
        # Get channel info from Twitch API
        access_token = twitch_api.get_app_access_token()
        user = twitch_api.get_user_info(access_token, user_id=None)  # Would need to modify to search by name
        
        # For now, create with provided data
        channel_id = db.twitch_channels.insert(
            channel_name=channel_name,
            broadcaster_id=data.get("broadcaster_id", ""),
            channel_id=data.get("channel_id", ""),
            gateway_id=gateway_id,
            is_active=True
        )
        db.commit()
        
        return {"success": True, "channel_id": channel_id}
        
    except Exception as e:
        logger.error(f"Error adding channel: {str(e)}")
        raise HTTP(500, f"Error: {str(e)}")

@action("twitch/api/setup/<channel_id>")
def setup_channel_subscriptions(channel_id: str):
    """Setup EventSub subscriptions for a channel"""
    try:
        # Get channel record
        channel = db(db.twitch_channels.id == channel_id).select().first()
        if not channel:
            raise HTTP(404, "Channel not found")
        
        # Get app access token
        access_token = twitch_api.get_app_access_token()
        
        # Event types to subscribe to
        event_types = [
            "channel.follow",
            "channel.subscribe", 
            "channel.cheer",
            "channel.raid",
            "channel.subscription.gift"
        ]
        
        created_subscriptions = []
        
        for event_type in event_types:
            try:
                condition = {"broadcaster_user_id": channel.broadcaster_id}
                
                # Special handling for follow events (requires moderator)
                if event_type == "channel.follow":
                    condition["moderator_user_id"] = channel.broadcaster_id
                
                subscription = twitch_api.create_eventsub_subscription(access_token, event_type, condition)
                
                # Save to database
                db.twitch_subscriptions.insert(
                    subscription_id=subscription.id,
                    channel_id=channel.id,
                    event_type=event_type,
                    status=subscription.status,
                    cost=subscription.cost
                )
                
                created_subscriptions.append(dataclass_to_dict(subscription))
                
            except Exception as e:
                logger.error(f"Error creating subscription for {event_type}: {str(e)}")
        
        db.commit()
        return {"subscriptions": created_subscriptions}
        
    except Exception as e:
        logger.error(f"Error setting up subscriptions for channel {channel_id}: {str(e)}")
        raise HTTP(500, f"Error: {str(e)}")