"""
Database models for WaddleBot Identity Core Module
"""

from py4web import DAL, Field
from datetime import datetime
import os

# Database connection
db = DAL(
    os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost:5432/waddlebot'),
    pool_size=20,
    migrate=True,
    fake_migrate_all=False
)

# Platform identities linked to py4web auth users
db.define_table('platform_identities',
    Field('user_id', 'reference auth_user', notnull=True),
    Field('platform', 'string', length=20, notnull=True),  # twitch, discord, slack
    Field('platform_id', 'string', length=64, notnull=True),  # Platform-specific user ID
    Field('platform_username', 'string', length=128),
    Field('is_verified', 'boolean', default=False),
    Field('verified_at', 'datetime'),
    Field('verification_method', 'string', length=20),  # whisper, oauth, admin
    Field('metadata', 'json', default={}),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    format='%(platform)s:%(platform_username)s'
)

# Create unique index on platform + platform_id
db.executesql('CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_identity ON platform_identities (platform, platform_id) WHERE is_verified = true;')

# Pending identity verifications
db.define_table('identity_verifications',
    Field('user_id', 'reference auth_user', notnull=True),
    Field('source_platform', 'string', length=20, notnull=True),
    Field('source_username', 'string', length=128),
    Field('target_platform', 'string', length=20, notnull=True),
    Field('target_username', 'string', length=128, notnull=True),
    Field('target_platform_id', 'string', length=64),  # Set after verification
    Field('verification_code', 'string', length=10, notnull=True),
    Field('status', 'string', length=20, default='pending'),  # pending, completed, expired
    Field('verified_at', 'datetime'),
    Field('resend_count', 'integer', default=0),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime', notnull=True),
    format='%(source_platform)s->%(target_platform)s:%(target_username)s'
)

# User API keys for programmatic access
db.define_table('user_api_keys',
    Field('user_id', 'reference auth_user', notnull=True),
    Field('name', 'string', length=128, notnull=True),
    Field('api_key_hash', 'string', length=64, notnull=True, unique=True),  # SHA256 hash
    Field('is_active', 'boolean', default=True),
    Field('last_used_at', 'datetime'),
    Field('usage_count', 'integer', default=0),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime'),
    Field('revoked_at', 'datetime'),
    Field('regenerated_at', 'datetime'),
    Field('metadata', 'json', default={}),
    format='%(name)s'
)

# Identity activity audit log
db.define_table('identity_activity',
    Field('user_id', 'reference auth_user'),
    Field('action', 'string', length=50, notnull=True),  # link, verify, unlink, api_key_create, etc
    Field('platform', 'string', length=20),
    Field('platform_username', 'string', length=128),
    Field('ip_address', 'string', length=45),
    Field('user_agent', 'string', length=256),
    Field('success', 'boolean', default=True),
    Field('error_message', 'text'),
    Field('metadata', 'json', default={}),
    Field('created_at', 'datetime', default=datetime.utcnow),
    format='%(action)s by %(user_id)s'
)

# Platform whisper/DM capabilities
db.define_table('platform_capabilities',
    Field('platform', 'string', length=20, unique=True, notnull=True),
    Field('supports_whisper', 'boolean', default=False),
    Field('whisper_method', 'string', length=50),  # api, websocket, webhook
    Field('rate_limit', 'integer', default=60),  # messages per minute
    Field('api_endpoint', 'string', length=256),
    Field('requires_oauth', 'boolean', default=True),
    Field('oauth_scopes', 'list:string'),
    Field('is_active', 'boolean', default=True),
    Field('last_checked', 'datetime'),
    Field('metadata', 'json', default={}),
    format='%(platform)s'
)

# Pre-populate platform capabilities
if db(db.platform_capabilities).isempty():
    db.platform_capabilities.insert(
        platform='twitch',
        supports_whisper=True,
        whisper_method='api',
        rate_limit=100,
        api_endpoint='https://api.twitch.tv/helix/whispers',
        requires_oauth=True,
        oauth_scopes=['user:manage:whispers', 'user:read:email'],
        is_active=True
    )
    db.platform_capabilities.insert(
        platform='discord',
        supports_whisper=True,
        whisper_method='websocket',
        rate_limit=120,
        api_endpoint='wss://gateway.discord.gg',
        requires_oauth=False,
        oauth_scopes=[],
        is_active=True
    )
    db.platform_capabilities.insert(
        platform='slack',
        supports_whisper=True,
        whisper_method='api',
        rate_limit=60,
        api_endpoint='https://slack.com/api/conversations.open',
        requires_oauth=True,
        oauth_scopes=['chat:write', 'im:write'],
        is_active=True
    )
    db.commit()

# Identity linking rules and policies
db.define_table('identity_policies',
    Field('name', 'string', length=128, unique=True, notnull=True),
    Field('description', 'text'),
    Field('policy_type', 'string', length=50),  # linking, verification, api_key
    Field('rules', 'json', default={}),  # JSON rules for policy enforcement
    Field('is_active', 'boolean', default=True),
    Field('priority', 'integer', default=100),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    format='%(name)s'
)

# Session tracking for identity operations
db.define_table('identity_sessions',
    Field('session_id', 'string', length=64, unique=True, notnull=True),
    Field('user_id', 'reference auth_user'),
    Field('operation', 'string', length=50),  # link, verify, api_key
    Field('platform', 'string', length=20),
    Field('status', 'string', length=20, default='active'),
    Field('metadata', 'json', default={}),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime'),
    Field('completed_at', 'datetime'),
    format='%(session_id)s'
)

# OAuth sessions and state management
db.define_table('oauth_sessions',
    Field('session_id', 'string', length=64, unique=True, notnull=True),
    Field('provider', 'string', length=20, notnull=True),  # twitch, discord, slack
    Field('state', 'string', length=64, notnull=True),
    Field('code_verifier', 'string', length=128),  # For PKCE
    Field('redirect_uri', 'string', length=512),
    Field('user_id', 'reference auth_user'),  # Set after successful auth
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime', notnull=True),
    Field('completed_at', 'datetime'),
    Field('is_completed', 'boolean', default=False),
    Field('metadata', 'json', default={}),
    format='%(provider)s:%(session_id)s'
)

# OAuth tokens for platform API access
db.define_table('oauth_tokens',
    Field('user_id', 'reference auth_user', notnull=True),
    Field('provider', 'string', length=20, notnull=True),
    Field('access_token', 'text', notnull=True),  # Encrypted
    Field('refresh_token', 'text'),  # Encrypted
    Field('token_type', 'string', length=20, default='Bearer'),
    Field('scope', 'list:string'),
    Field('expires_at', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    Field('metadata', 'json', default={}),
    format='%(provider)s:%(user_id)s'
)

# Create unique index on provider + user_id for OAuth tokens
db.executesql('CREATE UNIQUE INDEX IF NOT EXISTS idx_oauth_tokens_user_provider ON oauth_tokens (user_id, provider) WHERE is_active = true;')

# OAuth provider user data cache
db.define_table('oauth_user_cache',
    Field('user_id', 'reference auth_user', notnull=True),
    Field('provider', 'string', length=20, notnull=True),
    Field('provider_user_id', 'string', length=64, notnull=True),
    Field('provider_username', 'string', length=128),
    Field('provider_email', 'string', length=256),
    Field('provider_display_name', 'string', length=128),
    Field('provider_avatar_url', 'string', length=512),
    Field('raw_user_data', 'json', default={}),
    Field('last_updated', 'datetime', default=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    format='%(provider)s:%(provider_username)s'
)

# Create unique index on provider + provider_user_id
db.executesql('CREATE UNIQUE INDEX IF NOT EXISTS idx_oauth_user_cache_provider_user ON oauth_user_cache (provider, provider_user_id);')

# Indexes for performance
db.executesql('CREATE INDEX IF NOT EXISTS idx_platform_identities_user ON platform_identities (user_id);')
db.executesql('CREATE INDEX IF NOT EXISTS idx_platform_identities_platform ON platform_identities (platform, platform_id);')
db.executesql('CREATE INDEX IF NOT EXISTS idx_identity_verifications_status ON identity_verifications (status, expires_at);')
db.executesql('CREATE INDEX IF NOT EXISTS idx_user_api_keys_active ON user_api_keys (user_id, is_active);')
db.executesql('CREATE INDEX IF NOT EXISTS idx_identity_activity_user ON identity_activity (user_id, created_at);')
db.executesql('CREATE INDEX IF NOT EXISTS idx_oauth_sessions_state ON oauth_sessions (state, expires_at);')
db.executesql('CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user ON oauth_tokens (user_id, provider);')
db.executesql('CREATE INDEX IF NOT EXISTS idx_oauth_user_cache_user ON oauth_user_cache (user_id, provider);')

# Commit schema
db.commit()