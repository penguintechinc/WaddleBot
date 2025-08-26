"""
Database models for Chat Filter Module
Combines censorship, spam detection, and URL blocking
"""

from datetime import datetime
from typing import Optional, List, Dict
import json

# For PostgreSQL integration
try:
    from pydal import DAL, Field
    from config import Config
    
    # Database connection
    db = DAL(
        Config.DATABASE_URL,
        pool_size=10,
        migrate=True,
        folder='databases'
    )
    
    # Community filter settings (combines all filter types)
    db.define_table(
        'filter_settings',
        Field('id', 'id'),
        Field('community_id', 'string', required=True, unique=True),
        Field('profanity_enabled', 'boolean', default=True),
        Field('spam_detection_enabled', 'boolean', default=True),
        Field('url_blocking_enabled', 'boolean', default=False),
        Field('use_default_profanity', 'boolean', default=True),
        Field('use_default_spam_patterns', 'boolean', default=True),
        Field('severity_actions', 'json'),  # {"mild": "warn", "moderate": "censor", "severe": "block"}
        Field('strike_policy', 'json'),     # {"strikes": 3, "action": "timeout", "duration": 300}
        Field('notification_channel', 'string'),  # Where to send mod alerts
        Field('log_violations', 'boolean', default=True),
        Field('auto_timeout', 'boolean', default=False),
        Field('timeout_duration', 'integer', default=300),  # seconds
        Field('created_at', 'datetime', default=datetime.utcnow),
        Field('updated_at', 'datetime', update=datetime.utcnow),
        Field('updated_by', 'string')
    )
    
    # Community-specific profanity words
    db.define_table(
        'censorship_words',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('word', 'string', required=True),
        Field('action', 'string', default='ban'),  # ban, allow, flag
        Field('severity', 'string', default='moderate'),  # mild, moderate, severe
        Field('category', 'string'),  # profanity, slur, spam, custom
        Field('added_by', 'string'),
        Field('reason', 'text'),
        Field('match_type', 'string', default='contains'),  # exact, contains, regex
        Field('case_sensitive', 'boolean', default=False),
        Field('created_at', 'datetime', default=datetime.utcnow)
    )
    
    # Community-specific spam patterns
    db.define_table(
        'spam_patterns',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('pattern', 'string', required=True),
        Field('action', 'string', default='block'),  # block, allow, flag
        Field('severity', 'string', default='moderate'),  # low, moderate, high
        Field('category', 'string'),  # promotional, repetitive, url, custom
        Field('confidence_threshold', 'integer', default=30),  # 0-100
        Field('added_by', 'string'),
        Field('reason', 'text'),
        Field('match_type', 'string', default='contains'),  # exact, contains, regex
        Field('case_sensitive', 'boolean', default=False),
        Field('created_at', 'datetime', default=datetime.utcnow)
    )
    
    # Community URL blocking settings
    db.define_table(
        'url_settings',
        Field('id', 'id'),
        Field('community_id', 'string', required=True, unique=True),
        Field('url_blocking_enabled', 'boolean', default=False),
        Field('allow_all_urls', 'boolean', default=True),
        Field('allowed_domains', 'json'),    # List of allowed domains
        Field('blocked_domains', 'json'),    # List of blocked domains
        Field('require_https', 'boolean', default=False),
        Field('block_ip_addresses', 'boolean', default=True),
        Field('block_shorteners', 'boolean', default=True),
        Field('trusted_shorteners', 'json'), # List of trusted URL shorteners
        Field('created_at', 'datetime', default=datetime.utcnow),
        Field('updated_at', 'datetime', update=datetime.utcnow),
        Field('updated_by', 'string')
    )
    
    # Filter violation history (combines all violation types)
    db.define_table(
        'filter_violations',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('user_id', 'string', required=True),
        Field('user_name', 'string'),
        Field('platform', 'string'),  # discord, twitch, slack
        Field('original_message', 'text'),
        Field('censored_message', 'text'),
        Field('filter_type', 'string'),  # profanity, spam, url, combined
        Field('violations', 'json'),  # List of matched words/patterns/urls
        Field('spam_score', 'integer', default=0),  # 0-100 spam confidence
        Field('severity', 'string'),  # mild, moderate, severe
        Field('action_taken', 'string'),  # warned, censored, blocked, timeout
        Field('strike_count', 'integer', default=1),
        Field('created_at', 'datetime', default=datetime.utcnow)
    )
    
    # User strike tracking (shared across all filter types)
    db.define_table(
        'filter_strikes',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('user_id', 'string', required=True),
        Field('profanity_strikes', 'integer', default=0),
        Field('spam_strikes', 'integer', default=0),
        Field('url_strikes', 'integer', default=0),
        Field('total_strikes', 'integer', default=0),
        Field('last_violation', 'datetime'),
        Field('timeout_until', 'datetime'),
        Field('is_banned', 'boolean', default=False),
        Field('ban_reason', 'text'),
        Field('updated_at', 'datetime', update=datetime.utcnow)
    )
    
    # Whitelist for trusted users (applies to all filters)
    db.define_table(
        'filter_whitelist',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('user_id', 'string', required=True),
        Field('user_name', 'string'),
        Field('whitelist_type', 'string', default='all'),  # all, profanity, spam, url
        Field('reason', 'text'),
        Field('added_by', 'string'),
        Field('expires_at', 'datetime'),  # Optional expiration
        Field('created_at', 'datetime', default=datetime.utcnow)
    )
    
    # Filter statistics and analytics
    db.define_table(
        'filter_stats',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('date', 'date', default=datetime.utcnow().date()),
        Field('messages_checked', 'integer', default=0),
        Field('profanity_violations', 'integer', default=0),
        Field('spam_violations', 'integer', default=0),
        Field('url_violations', 'integer', default=0),
        Field('messages_blocked', 'integer', default=0),
        Field('messages_warned', 'integer', default=0),
        Field('users_timed_out', 'integer', default=0),
        Field('users_banned', 'integer', default=0),
        Field('created_at', 'datetime', default=datetime.utcnow),
        Field('updated_at', 'datetime', update=datetime.utcnow)
    )
    
    # Create indexes for performance
    db.executesql('CREATE INDEX IF NOT EXISTS idx_censorship_words_community ON censorship_words(community_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_spam_patterns_community ON spam_patterns(community_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_filter_violations_user ON filter_violations(community_id, user_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_filter_strikes_user ON filter_strikes(community_id, user_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_filter_whitelist_user ON filter_whitelist(community_id, user_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_filter_stats_community_date ON filter_stats(community_id, date);')
    
    db.commit()
    
except ImportError:
    # Fallback if PyDAL not available
    db = None

class FilterSettings:
    """Community filter settings class"""
    
    def __init__(self, community_id: str):
        self.community_id = community_id
        self.profanity_enabled = True
        self.spam_detection_enabled = True
        self.url_blocking_enabled = False
        self.use_default_profanity = True
        self.use_default_spam_patterns = True
        self.severity_actions = {
            'mild': 'warn',
            'moderate': 'censor', 
            'severe': 'block'
        }
        self.strike_policy = {
            'strikes': 3,
            'action': 'timeout',
            'duration': 300
        }
        self.notification_channel = None
        self.log_violations = True
        self.auto_timeout = False
        self.timeout_duration = 300
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'community_id': self.community_id,
            'profanity_enabled': self.profanity_enabled,
            'spam_detection_enabled': self.spam_detection_enabled,
            'url_blocking_enabled': self.url_blocking_enabled,
            'use_default_profanity': self.use_default_profanity,
            'use_default_spam_patterns': self.use_default_spam_patterns,
            'severity_actions': json.dumps(self.severity_actions),
            'strike_policy': json.dumps(self.strike_policy),
            'notification_channel': self.notification_channel,
            'log_violations': self.log_violations,
            'auto_timeout': self.auto_timeout,
            'timeout_duration': self.timeout_duration,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary"""
        instance = cls(data['community_id'])
        instance.profanity_enabled = data.get('profanity_enabled', True)
        instance.spam_detection_enabled = data.get('spam_detection_enabled', True)
        instance.url_blocking_enabled = data.get('url_blocking_enabled', False)
        instance.use_default_profanity = data.get('use_default_profanity', True)
        instance.use_default_spam_patterns = data.get('use_default_spam_patterns', True)
        
        if isinstance(data.get('severity_actions'), str):
            instance.severity_actions = json.loads(data['severity_actions'])
        else:
            instance.severity_actions = data.get('severity_actions', instance.severity_actions)
        
        if isinstance(data.get('strike_policy'), str):
            instance.strike_policy = json.loads(data['strike_policy'])
        else:
            instance.strike_policy = data.get('strike_policy', instance.strike_policy)
        
        instance.notification_channel = data.get('notification_channel')
        instance.log_violations = data.get('log_violations', True)
        instance.auto_timeout = data.get('auto_timeout', False)
        instance.timeout_duration = data.get('timeout_duration', 300)
        
        return instance