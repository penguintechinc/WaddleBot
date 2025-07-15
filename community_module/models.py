"""
Database models for the Community module
Uses the same database as the router module
"""

from py4web import DAL, Field
import os
from datetime import datetime

# Database connection - use same as router module
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite://storage.db")

# Handle both postgres:// and postgresql:// URLs
def normalize_db_url(url):
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

DATABASE_URL = normalize_db_url(DATABASE_URL)

# Database connection
db = DAL(
    DATABASE_URL,
    pool_size=10,
    migrate=True,
    fake_migrate_all=False,
    check_reserved=['all']
)

# Import shared table definitions from router module
# These tables are already defined in the router module

# Communities table
communities = db.define_table(
    'communities',
    Field('id', 'id'),
    Field('name', 'string', required=True),
    Field('owners', 'json', required=True),
    Field('entity_groups', 'json', default=[]),
    Field('member_ids', 'json', default=[]),
    Field('description', 'text'),
    Field('is_active', 'boolean', default=True),
    Field('settings', 'json', default={}),
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Entity groups table
entity_groups = db.define_table(
    'entity_groups',
    Field('id', 'id'),
    Field('name', 'string', required=True),
    Field('platform', 'string', required=True),
    Field('server_id', 'string', required=True),
    Field('entity_ids', 'json', default=[]),
    Field('community_id', 'reference communities'),
    Field('is_active', 'boolean', default=True),
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

# Community memberships table
community_memberships = db.define_table(
    'community_memberships',
    Field('id', 'id'),
    Field('community_id', 'reference communities', required=True),
    Field('user_id', 'string', required=True),
    Field('role', 'string', default='member'),
    Field('joined_at', 'datetime', default=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    Field('invited_by', 'string'),
    migrate=True
)

# User context table for tracking current community context
user_context = db.define_table(
    'user_context',
    Field('id', 'id'),
    Field('user_id', 'string', required=True),
    Field('entity_id', 'string', required=True),
    Field('current_community_id', 'reference communities'),
    Field('set_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime'),  # Optional expiration
    migrate=True
)

# Global constants
GLOBAL_COMMUNITY_NAME = "Global Community"
GLOBAL_COMMUNITY_ID = 1