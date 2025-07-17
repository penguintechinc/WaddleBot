"""
Database models for Browser Source Core Module
"""

from datetime import datetime

def define_tables(db):
    """Define database tables for Browser Source module"""
    
    # Browser source tokens for unique community URLs
    db.define_table(
        'browser_source_tokens',
        db.Field('community_id', 'string', required=True),
        db.Field('source_type', 'string', required=True),  # ticker, media, general
        db.Field('token', 'string', required=True, unique=True),
        db.Field('is_active', 'boolean', default=True),
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # Create unique index for community_id + source_type
    db.browser_source_tokens._create_index('community_source_idx', 'community_id', 'source_type', unique=True)
    
    # Browser source display history
    db.define_table(
        'browser_source_history',
        db.Field('community_id', 'string', required=True),
        db.Field('source_type', 'string', required=True),  # ticker, media, general
        db.Field('content', 'text'),  # JSON content
        db.Field('session_id', 'string'),
        db.Field('module_name', 'string'),
        db.Field('duration', 'integer'),  # Display duration in seconds
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # Browser source access logs
    db.define_table(
        'browser_source_access_log',
        db.Field('community_id', 'string', required=True),
        db.Field('source_type', 'string', required=True),
        db.Field('ip_address', 'string'),
        db.Field('user_agent', 'string'),
        db.Field('referer', 'string'),
        db.Field('accessed_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # Active WebSocket connections tracking
    db.define_table(
        'browser_source_connections',
        db.Field('community_id', 'string', required=True),
        db.Field('source_type', 'string', required=True),
        db.Field('connection_id', 'string', required=True, unique=True),
        db.Field('ip_address', 'string'),
        db.Field('user_agent', 'string'),
        db.Field('connected_at', 'datetime', default=datetime.utcnow),
        db.Field('last_ping', 'datetime', default=datetime.utcnow),
        db.Field('is_active', 'boolean', default=True),
        migrate=True
    )
    
    # Ticker message queue
    db.define_table(
        'ticker_message_queue',
        db.Field('community_id', 'string', required=True),
        db.Field('message', 'text', required=True),
        db.Field('priority', 'integer', default=5),  # 1-10 (1=highest)
        db.Field('duration', 'integer', default=10),  # Display duration in seconds
        db.Field('style', 'string', default='default'),
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        db.Field('scheduled_at', 'datetime', default=datetime.utcnow),
        db.Field('processed_at', 'datetime'),
        db.Field('is_processed', 'boolean', default=False),
        migrate=True
    )
    
    # Media display queue
    db.define_table(
        'media_display_queue',
        db.Field('community_id', 'string', required=True),
        db.Field('media_type', 'string', required=True),  # youtube, spotify, image, video
        db.Field('media_url', 'string'),
        db.Field('media_data', 'text'),  # JSON data
        db.Field('duration', 'integer', default=30),
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        db.Field('scheduled_at', 'datetime', default=datetime.utcnow),
        db.Field('processed_at', 'datetime'),
        db.Field('is_processed', 'boolean', default=False),
        migrate=True
    )
    
    # General content queue
    db.define_table(
        'general_content_queue',
        db.Field('community_id', 'string', required=True),
        db.Field('content_type', 'string', required=True),  # html, form, announcement
        db.Field('content', 'text', required=True),
        db.Field('style', 'text'),  # JSON style data
        db.Field('duration', 'integer', default=0),  # 0 = permanent until replaced
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        db.Field('scheduled_at', 'datetime', default=datetime.utcnow),
        db.Field('processed_at', 'datetime'),
        db.Field('is_processed', 'boolean', default=False),
        migrate=True
    )
    
    # Browser source settings per community
    db.define_table(
        'browser_source_settings',
        db.Field('community_id', 'string', required=True, unique=True),
        db.Field('ticker_enabled', 'boolean', default=True),
        db.Field('ticker_speed', 'integer', default=50),  # Pixels per second
        db.Field('ticker_style', 'text'),  # JSON style settings
        db.Field('media_enabled', 'boolean', default=True),
        db.Field('media_auto_hide', 'boolean', default=True),
        db.Field('media_style', 'text'),  # JSON style settings
        db.Field('general_enabled', 'boolean', default=True),
        db.Field('general_style', 'text'),  # JSON style settings
        db.Field('theme', 'string', default='default'),
        db.Field('custom_css', 'text'),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # Browser source analytics
    db.define_table(
        'browser_source_analytics',
        db.Field('community_id', 'string', required=True),
        db.Field('source_type', 'string', required=True),
        db.Field('event_type', 'string', required=True),  # view, click, interaction
        db.Field('event_data', 'text'),  # JSON event data
        db.Field('ip_address', 'string'),
        db.Field('user_agent', 'string'),
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # Message templates for different types
    db.define_table(
        'browser_source_templates',
        db.Field('community_id', 'string', required=True),
        db.Field('source_type', 'string', required=True),
        db.Field('template_name', 'string', required=True),
        db.Field('template_html', 'text', required=True),
        db.Field('template_css', 'text'),
        db.Field('template_js', 'text'),
        db.Field('is_active', 'boolean', default=True),
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    db.commit()