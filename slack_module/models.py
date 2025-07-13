"""
Database models for the Slack module
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

# Slack app installation tokens
db.define_table(
    'slack_tokens',
    Field('team_id', 'string', required=True, unique=True),
    Field('bot_token', 'text', required=True),
    Field('user_token', 'text'),
    Field('app_id', 'string', required=True),
    Field('enterprise_id', 'string'),
    Field('scopes', 'json'),
    Field('is_active', 'boolean', default=True),
    Field('installed_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Slack workspaces/teams being monitored
db.define_table(
    'slack_teams',
    Field('team_id', 'string', required=True, unique=True),
    Field('team_name', 'string', required=True),
    Field('team_domain', 'string'),
    Field('enterprise_id', 'string'),
    Field('is_active', 'boolean', default=True),
    Field('gateway_id', 'string'),  # Reference to gateway system
    Field('config', 'json'),
    Field('member_count', 'integer', default=0),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Slack channels being monitored
db.define_table(
    'slack_channels',
    Field('channel_id', 'string', required=True, unique=True),
    Field('channel_name', 'string', required=True),
    Field('channel_type', 'string', required=True),  # public_channel, private_channel, im, mpim
    Field('team_id', 'reference slack_teams', required=True),
    Field('is_monitored', 'boolean', default=True),
    Field('is_archived', 'boolean', default=False),
    Field('webhook_url', 'string'),
    Field('config', 'json'),
    Field('topic', 'text'),
    Field('purpose', 'text'),
    Field('member_count', 'integer', default=0),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Slack events log
db.define_table(
    'slack_events',
    Field('event_id', 'string', required=True, unique=True),
    Field('event_type', 'string', required=True),  # message, member_joined_channel, reaction_added, etc.
    Field('team_id', 'reference slack_teams'),
    Field('channel_id', 'reference slack_channels'),
    Field('user_id', 'string'),
    Field('user_name', 'string'),
    Field('event_data', 'json'),
    Field('processed', 'boolean', default=False),
    Field('processed_at', 'datetime'),
    Field('event_timestamp', 'string'),  # Slack timestamp
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Activity tracking for Slack
db.define_table(
    'slack_activities',
    Field('event_id', 'reference slack_events'),
    Field('activity_type', 'string', required=True),  # message, reaction, join, file_share, etc.
    Field('user_id', 'string', required=True),
    Field('user_name', 'string', required=True),
    Field('amount', 'integer', default=0),  # activity points
    Field('message', 'text'),
    Field('team_id', 'reference slack_teams'),
    Field('channel_id', 'reference slack_channels'),
    Field('context_sent', 'boolean', default=False),
    Field('context_response', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Slack slash commands
db.define_table(
    'slack_commands',
    Field('command_name', 'string', required=True),
    Field('team_id', 'reference slack_teams'),
    Field('description', 'text'),
    Field('usage_hint', 'string'),
    Field('response_template', 'text'),
    Field('is_enabled', 'boolean', default=True),
    Field('usage_count', 'integer', default=0),
    Field('last_used', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Slack users cache
db.define_table(
    'slack_users',
    Field('user_id', 'string', required=True),
    Field('team_id', 'reference slack_teams', required=True),
    Field('username', 'string', required=True),
    Field('real_name', 'string'),
    Field('display_name', 'string'),
    Field('email', 'string'),
    Field('is_bot', 'boolean', default=False),
    Field('is_admin', 'boolean', default=False),
    Field('is_owner', 'boolean', default=False),
    Field('is_restricted', 'boolean', default=False),
    Field('profile', 'json'),
    Field('timezone', 'string'),
    Field('last_seen', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# WaddleBot Core servers table (shared across all collectors)
db.define_table(
    'servers',
    Field('id', 'id'),
    Field('owner', 'string', required=True),
    Field('platform', 'string', required=True),  # slack, discord, twitch, etc.
    Field('channel', 'string', required=True),   # channel name/id
    Field('server_id', 'string'),               # team/workspace id for Slack
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