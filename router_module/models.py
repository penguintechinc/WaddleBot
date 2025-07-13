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
    Field('response_action', 'string', required=True), # chat, media, ticker
    Field('response_data', 'json'),                   # Response content
    Field('media_type', 'string'),                    # video, image, audio (for media action)
    Field('media_url', 'string'),                     # Media URL (for media action)
    Field('ticker_text', 'string'),                   # Ticker content (for ticker action)
    Field('ticker_duration', 'integer'),              # Ticker display duration in seconds
    Field('chat_message', 'text'),                    # Chat response (for chat action)
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
    
except Exception as e:
    # Indexes might already exist or DB might not support them
    pass

# Commit the database changes
db.commit()