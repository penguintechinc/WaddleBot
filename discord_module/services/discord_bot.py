"""
Discord bot service using py-cord
Handles Discord events and integrates with WaddleBot core
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import discord
from discord.ext import commands, tasks

from ..models import db
from ..config import load_config, ACTIVITY_POINTS, MONITORED_EVENTS
from ..dataclasses import (
    DiscordUser, DiscordGuild, DiscordChannel, DiscordMessage, DiscordMember,
    DiscordReaction, DiscordVoiceState, MessageEvent, ReactionEvent, MemberEvent,
    VoiceEvent, ContextPayload, IdentityPayload, dataclass_to_dict
)
from .core_api import core_api

logger = logging.getLogger(__name__)

# Load configuration
discord_config, waddlebot_config = load_config()

class WaddleBotDiscord(commands.Bot):
    """Main Discord bot class"""
    
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.reactions = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=discord_config.command_prefix,
            intents=intents,
            application_id=discord_config.application_id
        )
        
        self.core_api = core_api
        self.monitored_servers = {}
        self.voice_sessions = {}  # Track voice session durations
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Discord bot is starting up...")
        
        # Register with core API
        await self.register_with_core()
        
        # Load monitored servers
        await self.load_monitored_servers()
        
        # Start background tasks
        self.heartbeat_task.start()
        self.voice_tracker.start()
        
        logger.info("Discord bot setup complete")
    
    async def register_with_core(self):
        """Register this bot instance with the core API"""
        try:
            success = self.core_api.register_module()
            if success:
                logger.info("Successfully registered with core API")
            else:
                logger.error("Failed to register with core API")
        except Exception as e:
            logger.error(f"Error registering with core API: {str(e)}")
    
    async def load_monitored_servers(self):
        """Load list of servers to monitor from core API"""
        try:
            servers = self.core_api.get_monitored_servers()
            self.monitored_servers = {server['server_id']: server for server in servers}
            logger.info(f"Loaded {len(servers)} servers to monitor")
        except Exception as e:
            logger.error(f"Error loading monitored servers: {str(e)}")
    
    @tasks.loop(minutes=5)
    async def heartbeat_task(self):
        """Send heartbeat to core API"""
        try:
            self.core_api.send_heartbeat()
        except Exception as e:
            logger.error(f"Error sending heartbeat: {str(e)}")
    
    @tasks.loop(minutes=1)
    async def voice_tracker(self):
        """Track voice session durations"""
        current_time = datetime.utcnow()
        
        for session_key, session_data in list(self.voice_sessions.items()):
            duration = current_time - session_data['start_time']
            minutes = int(duration.total_seconds() / 60)
            
            if minutes > 0:
                # Award points for voice time
                await self.process_activity(
                    guild_id=session_data['guild_id'],
                    user_id=session_data['user_id'],
                    user_name=session_data['user_name'],
                    activity_type="voice_time",
                    amount=minutes * ACTIVITY_POINTS.get("voice_time", 1),
                    message=f"Voice activity for {minutes} minutes"
                )
                
                # Update start time
                self.voice_sessions[session_key]['start_time'] = current_time
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {str(e)}")
    
    async def on_message(self, message: discord.Message):
        """Handle message events"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if this guild is monitored
        if not self.is_monitored_guild(message.guild.id if message.guild else None):
            return
        
        try:
            # Log the event
            event_id = await self.log_discord_event(
                event_type="message",
                guild_id=str(message.guild.id) if message.guild else None,
                channel_id=str(message.channel.id),
                user_id=str(message.author.id),
                user_name=message.author.display_name,
                event_data={
                    "content": message.content,
                    "message_id": str(message.id),
                    "channel_name": message.channel.name if hasattr(message.channel, 'name') else None,
                    "attachments": len(message.attachments),
                    "embeds": len(message.embeds)
                }
            )
            
            # Process activity
            await self.process_activity(
                guild_id=str(message.guild.id) if message.guild else None,
                user_id=str(message.author.id),
                user_name=message.author.display_name,
                activity_type="message",
                amount=ACTIVITY_POINTS.get("message", 5),
                message=f"Message in #{message.channel.name if hasattr(message.channel, 'name') else 'DM'}",
                event_id=event_id
            )
            
            # Process commands
            await self.process_commands(message)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle reaction add events"""
        if user.bot:
            return
        
        if not self.is_monitored_guild(reaction.message.guild.id if reaction.message.guild else None):
            return
        
        try:
            # Log the event
            event_id = await self.log_discord_event(
                event_type="reaction_add",
                guild_id=str(reaction.message.guild.id) if reaction.message.guild else None,
                channel_id=str(reaction.message.channel.id),
                user_id=str(user.id),
                user_name=user.display_name,
                event_data={
                    "emoji": str(reaction.emoji),
                    "message_id": str(reaction.message.id),
                    "message_author": str(reaction.message.author.id)
                }
            )
            
            # Process activity
            await self.process_activity(
                guild_id=str(reaction.message.guild.id) if reaction.message.guild else None,
                user_id=str(user.id),
                user_name=user.display_name,
                activity_type="reaction",
                amount=ACTIVITY_POINTS.get("reaction", 2),
                message=f"Reacted with {reaction.emoji}",
                event_id=event_id
            )
            
        except Exception as e:
            logger.error(f"Error processing reaction: {str(e)}")
    
    async def on_member_join(self, member: discord.Member):
        """Handle member join events"""
        if not self.is_monitored_guild(str(member.guild.id)):
            return
        
        try:
            # Log the event
            event_id = await self.log_discord_event(
                event_type="member_join",
                guild_id=str(member.guild.id),
                user_id=str(member.id),
                user_name=member.display_name,
                event_data={
                    "username": member.name,
                    "discriminator": member.discriminator,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "account_created": member.created_at.isoformat()
                }
            )
            
            # Process activity
            await self.process_activity(
                guild_id=str(member.guild.id),
                user_id=str(member.id),
                user_name=member.display_name,
                activity_type="member_join",
                amount=ACTIVITY_POINTS.get("member_join", 10),
                message=f"Joined server {member.guild.name}",
                event_id=event_id
            )
            
        except Exception as e:
            logger.error(f"Error processing member join: {str(e)}")
    
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state changes"""
        if member.bot:
            return
        
        if not self.is_monitored_guild(str(member.guild.id)):
            return
        
        try:
            session_key = f"{member.guild.id}:{member.id}"
            
            # User joined a voice channel
            if before.channel is None and after.channel is not None:
                # Log the event
                event_id = await self.log_discord_event(
                    event_type="voice_join",
                    guild_id=str(member.guild.id),
                    user_id=str(member.id),
                    user_name=member.display_name,
                    event_data={
                        "channel_id": str(after.channel.id),
                        "channel_name": after.channel.name
                    }
                )
                
                # Start tracking session
                self.voice_sessions[session_key] = {
                    'guild_id': str(member.guild.id),
                    'user_id': str(member.id),
                    'user_name': member.display_name,
                    'start_time': datetime.utcnow()
                }
                
                # Process activity
                await self.process_activity(
                    guild_id=str(member.guild.id),
                    user_id=str(member.id),
                    user_name=member.display_name,
                    activity_type="voice_join",
                    amount=ACTIVITY_POINTS.get("voice_join", 8),
                    message=f"Joined voice channel {after.channel.name}",
                    event_id=event_id
                )
            
            # User left a voice channel
            elif before.channel is not None and after.channel is None:
                # Calculate session duration and award final points
                if session_key in self.voice_sessions:
                    session_data = self.voice_sessions[session_key]
                    duration = datetime.utcnow() - session_data['start_time']
                    minutes = int(duration.total_seconds() / 60)
                    
                    if minutes > 0:
                        await self.process_activity(
                            guild_id=str(member.guild.id),
                            user_id=str(member.id),
                            user_name=member.display_name,
                            activity_type="voice_time",
                            amount=minutes * ACTIVITY_POINTS.get("voice_time", 1),
                            message=f"Voice session ended after {minutes} minutes"
                        )
                    
                    del self.voice_sessions[session_key]
            
        except Exception as e:
            logger.error(f"Error processing voice state update: {str(e)}")
    
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Handle member updates (for boost detection)"""
        if not self.is_monitored_guild(str(after.guild.id)):
            return
        
        try:
            # Check for new boost
            if before.premium_since is None and after.premium_since is not None:
                # Log the event
                event_id = await self.log_discord_event(
                    event_type="member_boost",
                    guild_id=str(after.guild.id),
                    user_id=str(after.id),
                    user_name=after.display_name,
                    event_data={
                        "boosted_at": after.premium_since.isoformat()
                    }
                )
                
                # Process activity
                await self.process_activity(
                    guild_id=str(after.guild.id),
                    user_id=str(after.id),
                    user_name=after.display_name,
                    activity_type="boost",
                    amount=ACTIVITY_POINTS.get("boost", 100),
                    message=f"Boosted server {after.guild.name}",
                    event_id=event_id
                )
                
        except Exception as e:
            logger.error(f"Error processing member update: {str(e)}")
    
    def is_monitored_guild(self, guild_id: Optional[str]) -> bool:
        """Check if a guild is being monitored"""
        if guild_id is None:
            return False
        return guild_id in self.monitored_servers
    
    async def log_discord_event(self, event_type: str, guild_id: Optional[str] = None, 
                               channel_id: Optional[str] = None, user_id: Optional[str] = None,
                               user_name: Optional[str] = None, event_data: Dict = None) -> int:
        """Log Discord event to database"""
        try:
            # Generate unique event ID
            event_id = f"discord_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Get database references
            guild_record = None
            channel_record = None
            
            if guild_id:
                guild_record = db(db.discord_guilds.guild_id == guild_id).select().first()
            
            if channel_id:
                channel_record = db(db.discord_channels.channel_id == channel_id).select().first()
            
            # Insert event
            record_id = db.discord_events.insert(
                event_id=event_id,
                event_type=event_type,
                guild_id=guild_record.id if guild_record else None,
                channel_id=channel_record.id if channel_record else None,
                user_id=user_id,
                user_name=user_name,
                event_data=event_data or {},
                processed=False
            )
            
            db.commit()
            return record_id
            
        except Exception as e:
            logger.error(f"Error logging Discord event: {str(e)}")
            return None
    
    async def process_activity(self, guild_id: str, user_id: str, user_name: str, 
                              activity_type: str, amount: int, message: str, 
                              event_id: Optional[int] = None):
        """Process activity through WaddleBot context API"""
        try:
            # Get user context
            identity_payload = IdentityPayload(identity_name=user_name)
            context = self.core_api.get_context(dataclass_to_dict(identity_payload))
            
            if context:
                # Create context payload
                context_payload = ContextPayload(
                    userid=context['identity_id'],
                    activity=activity_type,
                    amount=amount,
                    text=message,
                    namespace=context['namespace_name'],
                    namespaceid=context['namespace_id'],
                    platform="Discord"
                )
                
                # Send to reputation API
                success = self.core_api.send_reputation(dataclass_to_dict(context_payload))
                
                # Log activity
                guild_record = db(db.discord_guilds.guild_id == guild_id).select().first()
                
                activity_id = db.discord_activities.insert(
                    event_id=event_id,
                    activity_type=activity_type,
                    user_id=user_id,
                    user_name=user_name,
                    amount=amount,
                    message=message,
                    guild_id=guild_record.id if guild_record else None,
                    context_sent=success,
                    context_response=context
                )
                
                db.commit()
                logger.info(f"Processed activity {activity_type} for {user_name}: {amount} points")
            else:
                logger.warning(f"No context found for user {user_name}")
                
        except Exception as e:
            logger.error(f"Error processing activity for {user_name}: {str(e)}")

# Global bot instance
bot = WaddleBotDiscord()