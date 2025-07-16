from pydal import DAL, Field
from datetime import datetime
import json
from config import Config

# Initialize database connection
db = DAL(Config.DATABASE_URL, migrate=True, pool_size=10)

# Kong Admin Users table
db.define_table('kong_admin_users',
    Field('username', 'string', unique=True, notnull=True, length=100),
    Field('email', 'string', unique=True, notnull=True, length=255),
    Field('full_name', 'string', length=255),
    Field('kong_consumer_id', 'string', unique=True, length=100),
    Field('api_key', 'string', unique=True, length=255),
    Field('permissions', 'json'),  # List of permissions
    Field('groups', 'json'),  # List of Kong ACL groups
    Field('is_active', 'boolean', default=True),
    Field('is_super_admin', 'boolean', default=False),
    Field('last_login', 'datetime'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', default=datetime.utcnow, update=datetime.utcnow),
    Field('created_by', 'string', length=100),
    Field('notes', 'text')
)

# Kong Admin Sessions table
db.define_table('kong_admin_sessions',
    Field('session_id', 'string', unique=True, notnull=True, length=100),
    Field('user_id', 'reference kong_admin_users', notnull=True),
    Field('ip_address', 'string', length=45),
    Field('user_agent', 'text'),
    Field('expires_at', 'datetime', notnull=True),
    Field('is_active', 'boolean', default=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('last_activity', 'datetime', default=datetime.utcnow)
)

# Kong Admin Audit Log table
db.define_table('kong_admin_audit_log',
    Field('action', 'string', notnull=True, length=100),
    Field('resource_type', 'string', notnull=True, length=100),  # 'user', 'consumer', 'service', etc.
    Field('resource_id', 'string', length=100),
    Field('details', 'json'),  # Action details
    Field('performed_by', 'reference kong_admin_users'),
    Field('ip_address', 'string', length=45),
    Field('user_agent', 'text'),
    Field('status', 'string', length=20, default='success'),  # 'success', 'failure', 'error'
    Field('error_message', 'text'),
    Field('created_at', 'datetime', default=datetime.utcnow)
)

# Kong Consumer Backup table (for disaster recovery)
db.define_table('kong_consumer_backup',
    Field('kong_consumer_id', 'string', notnull=True, length=100),
    Field('username', 'string', notnull=True, length=100),
    Field('consumer_data', 'json'),  # Full Kong consumer configuration
    Field('api_keys', 'json'),  # All API keys for this consumer
    Field('acl_groups', 'json'),  # ACL group memberships
    Field('rate_limits', 'json'),  # Rate limiting configuration
    Field('backup_type', 'string', length=20, default='manual'),  # 'manual', 'auto', 'migration'
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('created_by', 'reference kong_admin_users')
)

# Broker Configuration table
db.define_table('broker_config',
    Field('config_key', 'string', unique=True, notnull=True, length=100),
    Field('config_value', 'json'),
    Field('description', 'text'),
    Field('is_encrypted', 'boolean', default=False),
    Field('updated_at', 'datetime', default=datetime.utcnow, update=datetime.utcnow),
    Field('updated_by', 'reference kong_admin_users')
)

# Commit the schema
db.commit()

def init_default_config():
    """Initialize default broker configuration"""
    default_configs = [
        {
            'config_key': 'super_admin_permissions',
            'config_value': Config.DEFAULT_SUPER_ADMIN_PERMISSIONS,
            'description': 'Default permissions for super admin users'
        },
        {
            'config_key': 'api_key_expiry_days',
            'config_value': 365,
            'description': 'Default API key expiry in days (0 = no expiry)'
        },
        {
            'config_key': 'max_failed_logins',
            'config_value': 5,
            'description': 'Maximum failed login attempts before account lockout'
        },
        {
            'config_key': 'session_timeout_hours',
            'config_value': 24,
            'description': 'Session timeout in hours'
        },
        {
            'config_key': 'require_2fa',
            'config_value': False,
            'description': 'Require two-factor authentication for super admins'
        }
    ]
    
    for config in default_configs:
        existing = db(db.broker_config.config_key == config['config_key']).select().first()
        if not existing:
            db.broker_config.insert(**config)
    
    db.commit()

# Initialize default configuration
init_default_config()