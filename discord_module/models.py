"""
Database models for the Discord module
"""

from py4web import DAL, Field
import os
from datetime import datetime

# Database connection - PostgreSQL for production, SQLite for development
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite://storage.db")

# Handle both postgres:// and postgresql:// URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

db = DAL(
    DATABASE_URL,
    pool_size=10,
    migrate=True,
    fake_migrate_all=False,
    check_reserved=['all']
)

# Discord bot tokens and authentication
db.define_table(
    'discord_tokens',
    Field('guild_id', 'string', required=True, unique=True),
    Field('bot_token', 'text', required=True),
    Field('application_id', 'string', required=True),
    Field('public_key', 'string'),
    Field('permissions', 'json'),
    Field('is_active', 'boolean', default=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Discord guilds/servers being monitored
db.define_table(
    'discord_guilds',
    Field('guild_id', 'string', required=True, unique=True),
    Field('guild_name', 'string', required=True),
    Field('owner_id', 'string', required=True),
    Field('is_active', 'boolean', default=True),
    Field('prefix', 'string', default='!'),
    Field('welcome_channel', 'string'),
    Field('log_channel', 'string'),
    Field('gateway_id', 'string'),  # Reference to gateway system
    Field('config', 'json'),
    Field('member_count', 'integer', default=0),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Discord channels being monitored
db.define_table(
    'discord_channels',
    Field('channel_id', 'string', required=True, unique=True),
    Field('channel_name', 'string', required=True),
    Field('channel_type', 'string', required=True),  # text, voice, category, etc.
    Field('guild_id', 'reference discord_guilds', required=True),
    Field('is_monitored', 'boolean', default=True),
    Field('webhook_url', 'string'),
    Field('config', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Discord events log
db.define_table(
    'discord_events',
    Field('event_id', 'string', required=True, unique=True),
    Field('event_type', 'string', required=True),  # message, member_join, reaction, etc.
    Field('guild_id', 'reference discord_guilds'),
    Field('channel_id', 'reference discord_channels'),
    Field('user_id', 'string'),
    Field('user_name', 'string'),
    Field('event_data', 'json'),
    Field('processed', 'boolean', default=False),
    Field('processed_at', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Activity tracking for Discord
db.define_table(
    'discord_activities',
    Field('event_id', 'reference discord_events'),
    Field('activity_type', 'string', required=True),  # message, join, reaction, voice, etc.
    Field('user_id', 'string', required=True),
    Field('user_name', 'string', required=True),
    Field('amount', 'integer', default=0),  # activity points
    Field('message', 'text'),
    Field('guild_id', 'reference discord_guilds'),
    Field('channel_id', 'reference discord_channels'),
    Field('context_sent', 'boolean', default=False),
    Field('context_response', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Discord slash commands
db.define_table(
    'discord_commands',
    Field('command_name', 'string', required=True),
    Field('guild_id', 'reference discord_guilds'),
    Field('description', 'text'),
    Field('parameters', 'json'),
    Field('response_template', 'text'),
    Field('is_enabled', 'boolean', default=True),
    Field('usage_count', 'integer', default=0),
    Field('last_used', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# WaddleBot Core servers table (shared across all collectors)
db.define_table(
    'servers',
    Field('id', 'id'),
    Field('owner', 'string', required=True),
    Field('platform', 'string', required=True),  # discord, twitch, slack, etc.
    Field('channel', 'string', required=True),   # channel name/id
    Field('server_id', 'string'),               # server/guild id
    Field('is_active', 'boolean', default=True),
    Field('webhook_url', 'string'),             # platform-specific webhook URL
    Field('config', 'json'),                    # platform-specific configuration
    Field('last_activity', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Module registration table for tracking collector instances
db.define_table(
    'collector_modules',
    Field('module_name', 'string', required=True, unique=True),
    Field('module_version', 'string', required=True),
    Field('platform', 'string', required=True),
    Field('endpoint_url', 'string', required=True),
    Field('health_check_url', 'string'),
    Field('status', 'string', default='active'),  # active, inactive, error
    Field('last_heartbeat', 'datetime'),
    Field('config', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Commit the database changes
db.commit()