"""
Database models for the Router module
"""

from py4web import DAL, Field
import os
from datetime import datetime

# Database connections - Primary for writes, read replicas for reads
PRIMARY_DB_URL = os.environ.get("DATABASE_URL", "sqlite://storage.db")
READ_REPLICA_URL = os.environ.get("READ_REPLICA_URL", PRIMARY_DB_URL)

# Handle both postgres:// and postgresql:// URLs
def normalize_db_url(url):
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

PRIMARY_DB_URL = normalize_db_url(PRIMARY_DB_URL)
READ_REPLICA_URL = normalize_db_url(READ_REPLICA_URL)

# Primary database for writes
db = DAL(
    PRIMARY_DB_URL,
    pool_size=20,
    migrate=True,
    fake_migrate_all=False,
    check_reserved=['all']
)

# Read replica for command lookups (high performance)
db_read = DAL(
    READ_REPLICA_URL,
    pool_size=50,  # Higher pool for read operations
    migrate=False,  # No migrations on read replica
    fake_migrate_all=False,
    check_reserved=['all']
)

# Commands table - stores available commands and their routing information
db.define_table(
    'commands',
    Field('id', 'id'),
    Field('command', 'string', required=True),  # Command name (without prefix)
    Field('prefix', 'string', required=True),   # ! for local, # for community
    Field('description', 'text'),
    Field('location_url', 'string', required=True),  # Container/Lambda/OpenWhisk URL
    Field('location', 'string', required=True),      # internal (!) or community (#)
    Field('type', 'string', required=True),          # container, lambda, openwhisk, webhook
    Field('method', 'string', default='POST'),       # HTTP method
    Field('timeout', 'integer', default=30),         # Timeout in seconds
    Field('headers', 'json'),                        # Additional headers
    Field('auth_required', 'boolean', default=False),
    Field('rate_limit', 'integer', default=0),       # Requests per minute (0 = no limit)
    Field('is_active', 'boolean', default=True),
    Field('module_type', 'string', required=True),   # local, community (matches location)
    Field('module_id', 'string'),                    # Reference to marketplace module
    Field('version', 'string', default='1.0'),
    Field('trigger_type', 'string', default='command'), # command, event, both
    Field('event_types', 'json', default=[]),        # List of event types that trigger this module
    Field('priority', 'integer', default=100),       # Lower number = higher priority
    Field('execution_mode', 'string', default='sequential'), # sequential, parallel
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Entity mapping - defines platform+server+channel combinations
db.define_table(
    'entities',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True, unique=True),  # platform:server:channel
    Field('platform', 'string', required=True),  # discord, slack, twitch
    Field('server_id', 'string', required=True), # guild_id, team_id, channel_id
    Field('channel_id', 'string'),               # channel within server (optional for global)
    Field('owner', 'string', required=True),     # Owner/admin user
    Field('is_active', 'boolean', default=True),
    Field('config', 'json'),                     # Entity-specific configuration
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Command permissions - which entities have which commands enabled
db.define_table(
    'command_permissions',
    Field('id', 'id'),
    Field('command_id', 'reference commands', required=True),
    Field('entity_id', 'reference entities', required=True),
    Field('is_enabled', 'boolean', default=True),
    Field('config', 'json'),                     # Command-specific config for this entity
    Field('permissions', 'json'),               # User/role permissions
    Field('usage_count', 'integer', default=0), # Usage tracking
    Field('last_used', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Command executions - log of command invocations
db.define_table(
    'command_executions',
    Field('id', 'id'),
    Field('execution_id', 'string', required=True, unique=True),
    Field('command_id', 'reference commands', required=True),
    Field('entity_id', 'reference entities', required=True),
    Field('user_id', 'string', required=True),
    Field('user_name', 'string'),
    Field('message_content', 'text'),
    Field('parameters', 'json'),
    Field('location_url', 'string'),             # Actual URL called
    Field('request_payload', 'json'),
    Field('response_status', 'integer'),
    Field('response_data', 'json'),
    Field('execution_time_ms', 'integer'),
    Field('error_message', 'text'),
    Field('retry_count', 'integer', default=0),
    Field('status', 'string', default='pending'), # pending, success, failed, timeout
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('completed_at', 'datetime'),
    migrate=True
)

# Rate limiting tracking
db.define_table(
    'rate_limits',
    Field('id', 'id'),
    Field('command_id', 'reference commands', required=True),
    Field('entity_id', 'reference entities', required=True),
    Field('user_id', 'string', required=True),
    Field('window_start', 'datetime', required=True),
    Field('request_count', 'integer', default=1),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# String matching table for content moderation and auto-responses
db.define_table(
    'stringmatch',
    Field('id', 'id'),
    Field('string', 'text', required=True),     # String pattern to match
    Field('match_type', 'string', default='exact'),  # exact, contains, regex, word
    Field('case_sensitive', 'boolean', default=False),
    Field('enabled_entity_ids', 'json'),        # List of entity IDs where this rule applies
    Field('action', 'string', required=True),   # warn, block, command, webhook
    Field('command_to_execute', 'string'),      # Command to run if action=command
    Field('command_parameters', 'json'),        # Parameters for the command
    Field('webhook_url', 'string'),             # Webhook URL if action=webhook
    Field('warning_message', 'text'),           # Message for warn action
    Field('block_message', 'text'),             # Message for block action
    Field('priority', 'integer', default=100),  # Lower number = higher priority
    Field('is_active', 'boolean', default=True),
    Field('match_count', 'integer', default=0), # Usage tracking
    Field('last_matched', 'datetime'),
    Field('created_by', 'string'),              # User who created the rule
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Module responses from interaction modules and webhooks
db.define_table(
    'module_responses',
    Field('id', 'id'),
    Field('execution_id', 'string', required=True),  # Links to command_executions
    Field('module_name', 'string', required=True),    # Module that responded
    Field('success', 'boolean', required=True),       # Whether module ran properly
    Field('response_action', 'string', required=True), # chat, media, ticker, form, general
    Field('response_data', 'json'),                   # Response content
    Field('media_type', 'string'),                    # video, image, audio (for media action)
    Field('media_url', 'string'),                     # Media URL (for media action)
    Field('ticker_text', 'string'),                   # Ticker content (for ticker action)
    Field('ticker_duration', 'integer'),              # Ticker display duration in seconds
    Field('chat_message', 'text'),                    # Chat response (for chat action)
    Field('form_title', 'string'),                    # Form title (for form action)
    Field('form_description', 'text'),                # Form description (for form action)
    Field('form_fields', 'json'),                     # Form field definitions (for form action)
    Field('form_submit_url', 'string'),               # Form submission URL (for form action)
    Field('form_submit_method', 'string', default='POST'), # Form submission method (for form action)
    Field('form_callback_url', 'string'),             # Callback URL after form submission (for form action)
    Field('content_type', 'string'),                  # Content type (for general action)
    Field('content', 'text'),                         # HTML/text content (for general action)
    Field('duration', 'integer'),                     # Display duration in seconds (for general action)
    Field('style', 'json'),                           # Style information (for general action)
    Field('error_message', 'text'),                   # Error details if success=false
    Field('processing_time_ms', 'integer'),           # Module processing time
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Router statistics and monitoring
db.define_table(
    'router_stats',
    Field('id', 'id'),
    Field('metric_name', 'string', required=True),
    Field('metric_value', 'double', required=True),
    Field('labels', 'json'),                     # Additional metric labels
    Field('timestamp', 'datetime', default=datetime.utcnow),
    migrate=True
)

# WaddleBot Core servers table (shared across all modules)
db.define_table(
    'servers',
    Field('id', 'id'),
    Field('owner', 'string', required=True),
    Field('platform', 'string', required=True),
    Field('channel', 'string', required=True),
    Field('server_id', 'string'),
    Field('is_active', 'boolean', default=True),
    Field('webhook_url', 'string'),
    Field('config', 'json'),
    Field('last_activity', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Service accounts for API authentication
db.define_table(
    'service_accounts',
    Field('id', 'id'),
    Field('account_name', 'string', required=True, unique=True),
    Field('account_type', 'string', required=True),  # collector, interaction, webhook, admin
    Field('platform', 'string'),                     # platform for collector modules
    Field('api_key', 'string', required=True, unique=True),
    Field('api_key_hash', 'string', required=True),  # hashed version for security
    Field('permissions', 'json'),                    # list of allowed endpoints/actions
    Field('is_active', 'boolean', default=True),
    Field('last_used', 'datetime'),
    Field('usage_count', 'integer', default=0),
    Field('rate_limit', 'integer', default=1000),   # requests per hour
    Field('expires_at', 'datetime'),                 # optional expiration
    Field('created_by', 'string'),                   # admin who created it
    Field('description', 'text'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# API key usage tracking
db.define_table(
    'api_usage',
    Field('id', 'id'),
    Field('service_account_id', 'reference service_accounts', required=True),
    Field('endpoint', 'string', required=True),
    Field('method', 'string', required=True),
    Field('ip_address', 'string'),
    Field('user_agent', 'string'),
    Field('response_status', 'integer'),
    Field('response_time_ms', 'integer'),
    Field('request_size', 'integer'),
    Field('response_size', 'integer'),
    Field('timestamp', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Module registration table
db.define_table(
    'collector_modules',
    Field('module_name', 'string', required=True, unique=True),
    Field('module_version', 'string', required=True),
    Field('platform', 'string', required=True),
    Field('endpoint_url', 'string', required=True),
    Field('health_check_url', 'string'),
    Field('service_account_id', 'reference service_accounts'),
    Field('status', 'string', default='active'),
    Field('last_heartbeat', 'datetime'),
    Field('config', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Coordination table for dynamic server/channel assignment
db.define_table(
    'coordination',
    Field('id', 'id'),
    Field('platform', 'string', required=True),          # twitch, discord, slack, etc.
    Field('server_id', 'string', required=True),         # server/guild ID (or channel ID for Twitch)
    Field('channel_id', 'string'),                       # channel within server (null for Twitch)
    Field('entity_id', 'string', required=True),         # platform:server:channel format
    Field('claimed_by', 'string'),                       # container instance ID that claimed it
    Field('claimed_at', 'datetime'),                     # when it was claimed
    Field('status', 'string', default='available'),      # available, claimed, live, offline, error
    Field('is_live', 'boolean', default=False),          # whether stream/channel is currently live
    Field('live_since', 'datetime'),                     # when stream went live
    Field('viewer_count', 'integer', default=0),         # current viewer count (if applicable)
    Field('last_activity', 'datetime'),                  # last message/activity seen
    Field('last_check', 'datetime'),                     # last time status was checked
    Field('last_checkin', 'datetime'),                   # last time container checked in
    Field('claim_expires', 'datetime'),                  # when claim expires (for cleanup)
    Field('heartbeat_interval', 'integer', default=300), # heartbeat interval in seconds
    Field('error_count', 'integer', default=0),          # consecutive error count
    Field('metadata', 'json'),                           # platform-specific metadata
    Field('priority', 'integer', default=100),           # priority for claiming (lower = higher priority)
    Field('max_containers', 'integer', default=1),       # max containers that can claim this
    Field('config', 'json'),                             # entity-specific configuration
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Communities table for managing collections of entities
db.define_table(
    'communities',
    Field('id', 'id'),
    Field('name', 'string', required=True),
    Field('owners', 'json', required=True),           # List of user IDs who can manage this community
    Field('entity_groups', 'json', default=[]),       # List of entity group IDs
    Field('member_ids', 'json', default=[]),          # List of user IDs who are members
    Field('description', 'text'),
    Field('is_active', 'boolean', default=True),
    Field('settings', 'json', default={}),            # Community-specific settings
    Field('created_by', 'string', required=True),     # User ID who created the community
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Entity groups table for grouping entities by platform+server
db.define_table(
    'entity_groups',
    Field('id', 'id'),
    Field('name', 'string', required=True),
    Field('platform', 'string', required=True),       # discord, slack, etc. (not twitch)
    Field('server_id', 'string', required=True),      # guild_id, team_id, etc.
    Field('entity_ids', 'json', default=[]),          # List of entity IDs in this group
    Field('community_id', 'reference communities'),    # Which community this group belongs to
    Field('is_active', 'boolean', default=True),
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Reputation scoring configuration per community
db.define_table(
    'reputation_scoring',
    Field('id', 'id'),
    Field('event_name', 'string', required=True),     # follow, sub, message, reaction, etc.
    Field('event_score', 'integer', required=True),   # Points to award/deduct
    Field('community_id', 'reference communities', required=True),
    Field('is_active', 'boolean', default=True),
    Field('description', 'text'),                     # Description of what this event is
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# User reputation scores per community
db.define_table(
    'user_reputation',
    Field('id', 'id'),
    Field('user_id', 'string', required=True),        # User ID
    Field('community_id', 'reference communities', required=True),
    Field('current_score', 'integer', default=0),     # Current reputation score
    Field('total_events', 'integer', default=0),      # Total number of events processed
    Field('last_activity', 'datetime'),               # Last time score was updated
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Reputation event log for tracking all scoring events
db.define_table(
    'reputation_events',
    Field('id', 'id'),
    Field('user_id', 'string', required=True),
    Field('community_id', 'reference communities', required=True),
    Field('entity_id', 'string', required=True),      # Which entity the event came from
    Field('event_name', 'string', required=True),     # Event type that triggered scoring
    Field('event_score', 'integer', required=True),   # Points awarded/deducted
    Field('previous_score', 'integer', required=True), # User's score before this event
    Field('new_score', 'integer', required=True),     # User's score after this event
    Field('event_data', 'json'),                      # Additional event metadata
    Field('processed_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Community membership table for tracking user memberships (simplified)
db.define_table(
    'community_memberships',
    Field('id', 'id'),
    Field('community_id', 'reference communities', required=True),
    Field('user_id', 'string', required=True),
    Field('joined_at', 'datetime', default=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    Field('invited_by', 'string'),                    # User ID who invited this user
    migrate=True
)

# Community RBAC table for role-based access control (separate for performance)
db.define_table(
    'community_rbac',
    Field('id', 'id'),
    Field('community_id', 'reference communities', required=True),
    Field('user_id', 'string', required=True),
    Field('role', 'string', default='user'),          # user, moderator, owner
    Field('permissions', 'json', default={}),         # Additional granular permissions
    Field('assigned_by', 'string'),                   # User ID who assigned this role
    Field('assigned_at', 'datetime', default=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

# RBAC permissions table for granular permissions
db.define_table(
    'rbac_permissions',
    Field('id', 'id'),
    Field('name', 'string', required=True, unique=True),  # Permission name
    Field('description', 'text'),                     # Description of permission
    Field('category', 'string', default='general'),   # Category (moderation, management, etc.)
    Field('is_active', 'boolean', default=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Entity roles table for entity-specific permissions
db.define_table(
    'entity_roles',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True),      # Entity ID
    Field('user_id', 'string', required=True),        # User ID
    Field('role', 'string', required=True),           # user, moderator, owner
    Field('permissions', 'json', default={}),         # Additional granular permissions
    Field('assigned_by', 'string'),                   # User ID who assigned this role
    Field('assigned_at', 'datetime', default=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

# Default entity settings for entity groups
db.define_table(
    'entity_defaults',
    Field('id', 'id'),
    Field('entity_group_id', 'reference entity_groups', required=True),
    Field('default_entity_id', 'string', required=True),  # Default entity for group operations
    Field('is_active', 'boolean', default=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Copy table definitions to read replica for queries
for table_name in db.tables:
    if hasattr(db, table_name):
        table = getattr(db, table_name)
        # Create read-only version of the table
        setattr(db_read, table_name, table)

# Create indexes for performance
try:
    # Index for command lookups
    db.executesql('CREATE INDEX IF NOT EXISTS idx_commands_prefix_command ON commands(prefix, command) WHERE is_active = true;')
    
    # Index for command location/type lookups
    db.executesql('CREATE INDEX IF NOT EXISTS idx_commands_location_type ON commands(location, type) WHERE is_active = true;')
    
    # Index for entity lookups
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entities_entity_id ON entities(entity_id) WHERE is_active = true;')
    
    # Index for command permissions
    db.executesql('CREATE INDEX IF NOT EXISTS idx_command_permissions_lookup ON command_permissions(command_id, entity_id) WHERE is_enabled = true;')
    
    # Index for rate limiting
    db.executesql('CREATE INDEX IF NOT EXISTS idx_rate_limits_lookup ON rate_limits(command_id, entity_id, user_id, window_start);')
    
    # Index for string matching
    db.executesql('CREATE INDEX IF NOT EXISTS idx_stringmatch_active ON stringmatch(priority, is_active) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_stringmatch_action ON stringmatch(action, is_active) WHERE is_active = true;')
    
    # Index for module responses
    db.executesql('CREATE INDEX IF NOT EXISTS idx_module_responses_execution ON module_responses(execution_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_module_responses_module ON module_responses(module_name, created_at);')
    
    # Index for service accounts and API usage
    db.executesql('CREATE INDEX IF NOT EXISTS idx_service_accounts_api_key ON service_accounts(api_key, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_service_accounts_type ON service_accounts(account_type, platform);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_api_usage_account ON api_usage(service_account_id, timestamp);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint, timestamp);')
    
    # Index for coordination table
    db.executesql('CREATE INDEX IF NOT EXISTS idx_coordination_platform_status ON coordination(platform, status, priority);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_coordination_claimed_by ON coordination(claimed_by, claim_expires);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_coordination_entity_id ON coordination(entity_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_coordination_live ON coordination(platform, is_live, viewer_count);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_coordination_heartbeat ON coordination(claimed_by, last_check);')
    
    # Index for community tables
    db.executesql('CREATE INDEX IF NOT EXISTS idx_communities_name ON communities(name) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_communities_created_by ON communities(created_by) WHERE is_active = true;')
    
    # Index for entity groups
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_groups_platform_server ON entity_groups(platform, server_id) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_groups_community ON entity_groups(community_id) WHERE is_active = true;')
    
    # Index for reputation scoring
    db.executesql('CREATE INDEX IF NOT EXISTS idx_reputation_scoring_community_event ON reputation_scoring(community_id, event_name) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_reputation_scoring_event_name ON reputation_scoring(event_name) WHERE is_active = true;')
    
    # Index for user reputation
    db.executesql('CREATE INDEX IF NOT EXISTS idx_user_reputation_user_community ON user_reputation(user_id, community_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_user_reputation_community_score ON user_reputation(community_id, current_score);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_user_reputation_last_activity ON user_reputation(last_activity);')
    
    # Index for reputation events
    db.executesql('CREATE INDEX IF NOT EXISTS idx_reputation_events_user_community ON reputation_events(user_id, community_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_reputation_events_community_processed ON reputation_events(community_id, processed_at);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_reputation_events_entity_event ON reputation_events(entity_id, event_name);')
    
    # Index for community memberships
    db.executesql('CREATE INDEX IF NOT EXISTS idx_community_memberships_community_user ON community_memberships(community_id, user_id) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_community_memberships_user ON community_memberships(user_id) WHERE is_active = true;')
    
    # Index for community RBAC
    db.executesql('CREATE INDEX IF NOT EXISTS idx_community_rbac_community_user ON community_rbac(community_id, user_id) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_community_rbac_user_role ON community_rbac(user_id, role) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_community_rbac_community_role ON community_rbac(community_id, role) WHERE is_active = true;')
    
    # Index for RBAC permissions
    db.executesql('CREATE INDEX IF NOT EXISTS idx_rbac_permissions_name ON rbac_permissions(name) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_rbac_permissions_category ON rbac_permissions(category) WHERE is_active = true;')
    
    # Index for entity roles
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_roles_entity_user ON entity_roles(entity_id, user_id) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_roles_user_role ON entity_roles(user_id, role) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_roles_entity_role ON entity_roles(entity_id, role) WHERE is_active = true;')
    
    # Index for entity defaults
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_defaults_group ON entity_defaults(entity_group_id) WHERE is_active = true;')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_defaults_entity ON entity_defaults(default_entity_id) WHERE is_active = true;')
    
except Exception as e:
    # Indexes might already exist or DB might not support them
    pass

# Global community ID constant
GLOBAL_COMMUNITY_ID = 1  # Reserved ID for global community

# Commit the database changes
db.commit()