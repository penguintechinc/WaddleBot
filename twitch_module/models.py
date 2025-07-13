"""
Database models for the Twitch module
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

# Twitch authentication tokens
db.define_table(
    'twitch_tokens',
    Field('user_id', 'string', required=True),
    Field('access_token', 'text', required=True),
    Field('refresh_token', 'text', required=True),
    Field('expires_at', 'datetime', required=True),
    Field('scopes', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Twitch channels being monitored
db.define_table(
    'twitch_channels',
    Field('channel_id', 'string', required=True, unique=True),
    Field('channel_name', 'string', required=True),
    Field('broadcaster_id', 'string', required=True),
    Field('is_active', 'boolean', default=True),
    Field('webhook_secret', 'string'),
    Field('gateway_id', 'string'),  # Reference to gateway system
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# EventSub subscriptions
db.define_table(
    'twitch_subscriptions',
    Field('subscription_id', 'string', required=True, unique=True),
    Field('channel_id', 'reference twitch_channels', required=True),
    Field('event_type', 'string', required=True),
    Field('status', 'string', default='enabled'),
    Field('cost', 'integer', default=1),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Webhook events log
db.define_table(
    'twitch_events',
    Field('event_id', 'string', required=True, unique=True),
    Field('subscription_id', 'reference twitch_subscriptions'),
    Field('event_type', 'string', required=True),
    Field('broadcaster_user_id', 'string'),
    Field('broadcaster_user_name', 'string'),
    Field('user_id', 'string'),
    Field('user_name', 'string'),
    Field('event_data', 'json'),
    Field('processed', 'boolean', default=False),
    Field('processed_at', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Activity tracking
db.define_table(
    'twitch_activities',
    Field('event_id', 'reference twitch_events'),
    Field('activity_type', 'string', required=True),  # follow, sub, bits, raid, etc.
    Field('user_name', 'string', required=True),
    Field('amount', 'integer', default=0),  # bits amount, sub tier, etc.
    Field('message', 'text'),
    Field('channel_id', 'reference twitch_channels'),
    Field('context_sent', 'boolean', default=False),
    Field('context_response', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# WaddleBot Core servers table (shared across all collectors)
db.define_table(
    'servers',
    Field('id', 'id'),
    Field('owner', 'string', required=True),
    Field('platform', 'string', required=True),  # twitch, discord, slack, etc.
    Field('channel', 'string', required=True),   # channel name/id
    Field('server_id', 'string'),               # server/guild id (for Discord)
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