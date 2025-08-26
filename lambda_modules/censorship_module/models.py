"""
Database models for Censorship Module
Stores community-specific word lists and settings
"""

from datetime import datetime
from typing import Optional, List, Dict
import json

# For PostgreSQL integration (when not using DynamoDB)
try:
    from pydal import DAL, Field
    
    # Database connection
    db = DAL(
        'postgres://waddlebot:password@localhost/waddlebot',
        pool_size=10,
        migrate=True,
        folder='databases'
    )
    
    # Community censorship settings
    db.define_table(
        'censorship_settings',
        Field('id', 'id'),
        Field('community_id', 'string', required=True, unique=True),
        Field('enabled', 'boolean', default=True),
        Field('use_default_list', 'boolean', default=True),
        Field('severity_action', 'json'),  # {"mild": "warn", "moderate": "censor", "severe": "block"}
        Field('strike_policy', 'json'),    # {"strikes": 3, "action": "timeout", "duration": 300}
        Field('notification_channel', 'string'),  # Where to send mod alerts
        Field('log_violations', 'boolean', default=True),
        Field('auto_timeout', 'boolean', default=False),
        Field('timeout_duration', 'integer', default=300),  # seconds
        Field('created_at', 'datetime', default=datetime.utcnow),
        Field('updated_at', 'datetime', update=datetime.utcnow),
        Field('updated_by', 'string')
    )
    
    # Community-specific word lists
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
    
    # User violation history
    db.define_table(
        'censorship_violations',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('user_id', 'string', required=True),
        Field('user_name', 'string'),
        Field('platform', 'string'),  # discord, twitch, slack
        Field('original_message', 'text'),
        Field('censored_message', 'text'),
        Field('violations', 'json'),  # List of matched words
        Field('severity', 'string'),  # mild, moderate, severe
        Field('action_taken', 'string'),  # warned, censored, blocked, timeout
        Field('strike_count', 'integer', default=1),
        Field('created_at', 'datetime', default=datetime.utcnow)
    )
    
    # User strike tracking
    db.define_table(
        'censorship_strikes',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('user_id', 'string', required=True),
        Field('strike_count', 'integer', default=0),
        Field('last_violation', 'datetime'),
        Field('timeout_until', 'datetime'),
        Field('is_banned', 'boolean', default=False),
        Field('ban_reason', 'text'),
        Field('updated_at', 'datetime', update=datetime.utcnow)
    )
    
    # Whitelist for trusted users
    db.define_table(
        'censorship_whitelist',
        Field('id', 'id'),
        Field('community_id', 'string', required=True),
        Field('user_id', 'string', required=True),
        Field('user_name', 'string'),
        Field('reason', 'text'),
        Field('added_by', 'string'),
        Field('created_at', 'datetime', default=datetime.utcnow)
    )
    
    # Create indexes for performance
    db.executesql('CREATE INDEX IF NOT EXISTS idx_censorship_words_community ON censorship_words(community_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_censorship_violations_user ON censorship_violations(community_id, user_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_censorship_strikes_user ON censorship_strikes(community_id, user_id);')
    
    db.commit()
    
except ImportError:
    # Fallback if PyDAL not available (Lambda environment)
    pass

# DynamoDB Schema (for Lambda deployment)
DYNAMODB_TABLES = {
    'waddlebot_censorship_settings': {
        'TableName': 'waddlebot_censorship_settings',
        'KeySchema': [
            {'AttributeName': 'community_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'community_id', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'waddlebot_censorship_words': {
        'TableName': 'waddlebot_censorship_words',
        'KeySchema': [
            {'AttributeName': 'community_id', 'KeyType': 'HASH'},
            {'AttributeName': 'word', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'community_id', 'AttributeType': 'S'},
            {'AttributeName': 'word', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'waddlebot_censorship_violations': {
        'TableName': 'waddlebot_censorship_violations',
        'KeySchema': [
            {'AttributeName': 'community_id', 'KeyType': 'HASH'},
            {'AttributeName': 'violation_id', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'community_id', 'AttributeType': 'S'},
            {'AttributeName': 'violation_id', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'user_index',
                'Keys': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'waddlebot_censorship_strikes': {
        'TableName': 'waddlebot_censorship_strikes',
        'KeySchema': [
            {'AttributeName': 'community_id', 'KeyType': 'HASH'},
            {'AttributeName': 'user_id', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'community_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    }
}

class CensorshipSettings:
    """Community censorship settings"""
    
    def __init__(self, community_id: str):
        self.community_id = community_id
        self.enabled = True
        self.use_default_list = True
        self.severity_action = {
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
            'enabled': self.enabled,
            'use_default_list': self.use_default_list,
            'severity_action': json.dumps(self.severity_action),
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
        instance.enabled = data.get('enabled', True)
        instance.use_default_list = data.get('use_default_list', True)
        
        if isinstance(data.get('severity_action'), str):
            instance.severity_action = json.loads(data['severity_action'])
        else:
            instance.severity_action = data.get('severity_action', instance.severity_action)
        
        if isinstance(data.get('strike_policy'), str):
            instance.strike_policy = json.loads(data['strike_policy'])
        else:
            instance.strike_policy = data.get('strike_policy', instance.strike_policy)
        
        instance.notification_channel = data.get('notification_channel')
        instance.log_violations = data.get('log_violations', True)
        instance.auto_timeout = data.get('auto_timeout', False)
        instance.timeout_duration = data.get('timeout_duration', 300)
        
        return instance