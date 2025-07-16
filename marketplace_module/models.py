"""
Database models for the Marketplace module
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
    pool_size=15,
    migrate=True,
    fake_migrate_all=False,
    check_reserved=['all']
)

# Marketplace module definitions
db.define_table(
    'marketplace_modules',
    Field('id', 'id'),
    Field('module_id', 'string', required=True, unique=True),
    Field('name', 'string', required=True),
    Field('display_name', 'string', required=True),
    Field('description', 'text'),
    Field('long_description', 'text'),
    Field('version', 'string', required=True),
    Field('author', 'string', required=True),
    Field('author_email', 'string'),
    Field('website', 'string'),
    Field('repository', 'string'),
    Field('license', 'string', default='MIT'),
    Field('category', 'string', required=True),
    Field('tags', 'list:string'),
    Field('icon_url', 'string'),
    Field('screenshots', 'json'),
    Field('is_active', 'boolean', default=True),
    Field('is_featured', 'boolean', default=False),
    Field('is_verified', 'boolean', default=False),
    Field('download_count', 'integer', default=0),
    Field('rating_average', 'double', default=0.0),
    Field('rating_count', 'integer', default=0),
    Field('price', 'double', default=0.0),  # 0.0 = free
    Field('requires_approval', 'boolean', default=False),
    Field('min_waddlebot_version', 'string'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    Field('published_at', 'datetime'),
    migrate=True
)

# Module versions and releases
db.define_table(
    'module_versions',
    Field('id', 'id'),
    Field('module_id', 'reference marketplace_modules', required=True),
    Field('version', 'string', required=True),
    Field('changelog', 'text'),
    Field('download_url', 'string', required=True),
    Field('checksum', 'string'),
    Field('file_size', 'integer'),
    Field('installation_instructions', 'text'),
    Field('requirements', 'json'),  # Dependencies
    Field('compatibility', 'json'),  # Platform compatibility
    Field('is_stable', 'boolean', default=True),
    Field('is_latest', 'boolean', default=False),
    Field('download_count', 'integer', default=0),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Module commands that get registered in router
db.define_table(
    'module_commands',
    Field('id', 'id'),
    Field('module_id', 'reference marketplace_modules', required=True),
    Field('command', 'string', required=True),
    Field('description', 'text'),
    Field('usage', 'string'),
    Field('examples', 'text'),
    Field('location_url', 'string', required=True),
    Field('location', 'string', default='community'),    # internal or community
    Field('type', 'string', default='lambda'),           # container, lambda, openwhisk, webhook
    Field('method', 'string', default='POST'),
    Field('timeout', 'integer', default=30),
    Field('rate_limit', 'integer', default=60),
    Field('auth_required', 'boolean', default=False),
    Field('permissions_required', 'json'),
    Field('parameters', 'json'),  # Command parameter definitions
    Field('is_active', 'boolean', default=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Module installations per entity
db.define_table(
    'module_installations',
    Field('id', 'id'),
    Field('module_id', 'reference marketplace_modules', required=True),
    Field('entity_id', 'string', required=True),  # platform:server:channel
    Field('installed_version', 'string', required=True),
    Field('is_enabled', 'boolean', default=True),
    Field('config', 'json'),  # Module-specific configuration
    Field('installed_by', 'string', required=True),  # User who installed
    Field('installed_at', 'datetime', default=datetime.utcnow),
    Field('last_updated', 'datetime', update=datetime.utcnow),
    Field('usage_count', 'integer', default=0),
    Field('last_used', 'datetime'),
    migrate=True
)

# Module reviews and ratings
db.define_table(
    'module_reviews',
    Field('id', 'id'),
    Field('module_id', 'reference marketplace_modules', required=True),
    Field('user_id', 'string', required=True),
    Field('user_name', 'string', required=True),
    Field('rating', 'integer', required=True),  # 1-5 stars
    Field('title', 'string'),
    Field('review_text', 'text'),
    Field('is_verified_purchase', 'boolean', default=False),
    Field('helpful_votes', 'integer', default=0),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Module categories
db.define_table(
    'module_categories',
    Field('id', 'id'),
    Field('name', 'string', required=True, unique=True),
    Field('display_name', 'string', required=True),
    Field('description', 'text'),
    Field('icon', 'string'),
    Field('parent_category', 'reference module_categories'),
    Field('sort_order', 'integer', default=0),
    Field('is_active', 'boolean', default=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Entity permissions for marketplace access
db.define_table(
    'entity_permissions',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True),
    Field('user_id', 'string', required=True),
    Field('permission_type', 'string', required=True),  # admin, manage_modules, use_modules
    Field('granted_by', 'string', required=True),
    Field('granted_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime'),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

# Download tracking and analytics
db.define_table(
    'module_downloads',
    Field('id', 'id'),
    Field('module_id', 'reference marketplace_modules', required=True),
    Field('version', 'string', required=True),
    Field('entity_id', 'string', required=True),
    Field('user_id', 'string', required=True),
    Field('ip_address', 'string'),
    Field('user_agent', 'string'),
    Field('download_type', 'string', default='install'),  # install, update, reinstall
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Module usage statistics
db.define_table(
    'module_usage_stats',
    Field('id', 'id'),
    Field('module_id', 'reference marketplace_modules', required=True),
    Field('entity_id', 'string', required=True),
    Field('command', 'string', required=True),
    Field('usage_count', 'integer', default=1),
    Field('last_used', 'datetime', default=datetime.utcnow),
    Field('date', 'date', default=datetime.utcnow().date()),
    migrate=True
)

# WaddleBot Core tables (shared)
db.define_table(
    'entities',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True, unique=True),
    Field('platform', 'string', required=True),
    Field('server_id', 'string', required=True),
    Field('channel_id', 'string'),
    Field('owner', 'string', required=True),
    Field('is_active', 'boolean', default=True),
    Field('config', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Community subscriptions for paid modules
db.define_table(
    'community_subscriptions',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True, unique=True),
    Field('subscription_type', 'string', required=True),  # 'free', 'premium', 'enterprise'
    Field('subscription_status', 'string', required=True),  # 'active', 'expired', 'cancelled', 'suspended'
    Field('subscription_start', 'datetime', required=True),
    Field('subscription_end', 'datetime', required=True),
    Field('auto_renew', 'boolean', default=True),
    Field('payment_method', 'string'),  # 'stripe', 'paypal', 'manual'
    Field('payment_id', 'string'),  # External payment system ID
    Field('last_payment_date', 'datetime'),
    Field('next_payment_date', 'datetime'),
    Field('amount_paid', 'double', default=0.0),
    Field('currency', 'string', default='USD'),
    Field('grace_period_end', 'datetime'),  # Grace period after expiration
    Field('cancellation_reason', 'string'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Payment history for communities
db.define_table(
    'community_payments',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True),
    Field('payment_id', 'string', required=True),
    Field('payment_method', 'string', required=True),  # 'stripe', 'paypal'
    Field('amount', 'double', required=True),
    Field('currency', 'string', required=True),
    Field('payment_status', 'string', required=True),  # 'pending', 'completed', 'failed', 'refunded'
    Field('payment_date', 'datetime', required=True),
    Field('description', 'string'),
    Field('metadata', 'json'),  # Payment processor metadata
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Commands table (synchronized with router)
db.define_table(
    'commands',
    Field('id', 'id'),
    Field('command', 'string', required=True),
    Field('prefix', 'string', required=True),
    Field('description', 'text'),
    Field('location_url', 'string', required=True),
    Field('location', 'string', required=True),      # internal (!) or community (#)
    Field('type', 'string', required=True),          # container, lambda, openwhisk, webhook
    Field('method', 'string', default='POST'),
    Field('timeout', 'integer', default=30),
    Field('headers', 'json'),
    Field('auth_required', 'boolean', default=False),
    Field('rate_limit', 'integer', default=0),
    Field('is_active', 'boolean', default=True),
    Field('module_type', 'string', required=True),   # local, community (matches location)
    Field('module_id', 'string'),
    Field('version', 'string', default='1.0'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Command permissions (synchronized with router)
db.define_table(
    'command_permissions',
    Field('id', 'id'),
    Field('command_id', 'reference commands', required=True),
    Field('entity_id', 'reference entities', required=True),
    Field('is_enabled', 'boolean', default=True),
    Field('config', 'json'),
    Field('permissions', 'json'),
    Field('usage_count', 'integer', default=0),
    Field('last_used', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Create indexes for performance
try:
    # Marketplace search indexes
    db.executesql('CREATE INDEX IF NOT EXISTS idx_marketplace_modules_search ON marketplace_modules(name, category, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_marketplace_modules_featured ON marketplace_modules(is_featured, rating_average) WHERE is_active = true;')
    
    # Installation lookup
    db.executesql('CREATE INDEX IF NOT EXISTS idx_module_installations_entity ON module_installations(entity_id, is_enabled);')
    
    # Usage tracking
    db.executesql('CREATE INDEX IF NOT EXISTS idx_module_usage_stats_lookup ON module_usage_stats(module_id, entity_id, date);')
    
    # Subscription lookup
    db.executesql('CREATE INDEX IF NOT EXISTS idx_community_subscriptions_entity ON community_subscriptions(entity_id, subscription_status);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_community_subscriptions_expiry ON community_subscriptions(subscription_end, subscription_status);')
    
    # Payment history
    db.executesql('CREATE INDEX IF NOT EXISTS idx_community_payments_entity ON community_payments(entity_id, payment_date);')
    
except Exception as e:
    # Indexes might already exist
    pass

# Commit the database changes
db.commit()